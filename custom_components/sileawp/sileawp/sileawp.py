# -*- coding: utf-8 -*-
"""Asynchronous Python client for the Silea waste pickup API."""
import asyncio
import json
import socket
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from typing import Dict, Optional

import aiohttp
import async_timeout
from yarl import URL
from re import sub

from .__version__ import __version__
from .const import API_BASE_URI, API_HOST, API_TO_SERVICE
from .exceptions import (
    SileaWpAddressError,
    SileaWpConnectionError,
    SileaWpError,
)

import logging

_LOGGER = logging.getLogger(__name__)


class SileaWp:
    """Main class for handling connections with Silea waste pickup."""

    def __init__(
        self,
        client_id: str,
        street_id: str,
        loop=None,
        request_timeout: int = 10,
        session=None,
        user_agent: str = None,
    ):
        """Initialize connection with Silea waste pickup."""
        self._loop = loop
        self._session = session
        self._close_session = False

        self.street_id = street_id
        self.client_id = client_id

        self.request_timeout = request_timeout
        self.user_agent = user_agent

        self._unique_id = None
        self._pickup = {}  # type: Dict[str, datetime]

        if self._loop is None:
            self._loop = asyncio.get_event_loop()

        if self._session is None:
            self._session = aiohttp.ClientSession(loop=self._loop)
            self._close_session = True

        if self.user_agent is None:
            self.user_agent = "SileaWpClient/{}".format(__version__)

    def get_next_service(self, calendar: list) -> dict:
        _LOGGER.debug("Calculating next services from calendar data")
        services = {}
        now = datetime.now()
        for pickup in calendar:
            service_date = pickup["date"]
            if service_date < now:
                continue

            services[pickup["service"]] = (
                service_date
                if (
                    services.get(pickup["service"]) is None
                    or service_date < services[pickup["service"]]
                )
                else services[pickup["service"]]
            )

        return services

    async def get_calendar(self):
        _LOGGER.info("Fetching calendar from Silea waste pickup API")

        start_date = date.today()
        months_limit = 3
        iteration = 0

        calendar = []

        while iteration < months_limit:

            # Calculate the first day of the month, handling year rollover
            fetch_date = datetime(start_date.year, start_date.month, 1) + relativedelta(months=iteration)

            month_calendar = await self._get_calendar(f"{fetch_date.month}_{fetch_date.year}")
            if len(month_calendar):
                calendar.extend(month_calendar)

            iteration += 1

        pickups = []
        for day in calendar:
            pickup_day = datetime.fromisoformat(day["date"]["date"])

            for pickup in day.get("services", []):
                _LOGGER.debug("Found pickup: %s on %s", pickup, pickup_day)
                service_type = pickup["service"]
                service = API_TO_SERVICE.get(service_type)
                if service is None:
                    _LOGGER.warning("Unknown service type %s, skipping", service_type)
                    continue

                pickup_time = datetime.strptime(
                    sub(" -.+", "", pickup["hours"]), "%H:%M"
                )
                pickup_date = pickup_day.replace(
                    hour=pickup_time.hour,
                    minute=pickup_time.minute,
                    second=0,
                )

                pickups.append({"service": service, "date": pickup_date})

        return pickups

    async def _get_calendar(self, month: str) -> dict:
        raw_data = {
            "action": "get_calendar",
            "id_cliente": self.client_id,
            "id_via": self.street_id,
            "id_mese": month,
        }
        headers = {
            "user-agent": self.user_agent,
            "origin": "https://www.sileaspa.it",
            "authority": "www.sileaspa.it",
            "referer": "https://www.sileaspa.it/calendario-raccolta-rifiuti/",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Cookie": "cmplz_banner-status=dismissed",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01",
        }

        calendar_url = ""

        url = URL.build(
            scheme="https", host=API_HOST, port=443, path=API_BASE_URI
        ).join(URL(calendar_url))

        _LOGGER.debug("Requesting calendar data from %s with payload %s", url, raw_data )

        try:
            with async_timeout.timeout(self.request_timeout):
                response = await self._session.request(
                    "POST",
                    url,
                    data=raw_data,
                    headers=headers,
                    ssl=True,
                )
        except asyncio.TimeoutError as exception:
            raise SileaWpConnectionError(
                "Timeout occurred while connecting to Silea waste pickup API."
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            raise SileaWpConnectionError(
                "Error occurred while communicating with Silea waste pickup."
            ) from exception

        content_type = response.headers.get("Content-Type", "")
        if (response.status // 100) in [4, 5]:
            contents = await response.read()
            response.close()

            if content_type == "application/json":
                raise SileaWpError(response.status, json.loads(contents.decode("utf8")))
            raise SileaWpError(response.status, {"message": contents.decode("utf8")})

        if "application/json" in response.headers["Content-Type"]:
            return await response.json()
        return await response.text()

    def unique_id(self) -> Optional[str]:
        """Return unique address ID."""
        if self._unique_id is None:
            self._unique_id = f"IDCliente={self.client_id}|IDVia={self.street_id}"
        return self._unique_id

    async def update(self) -> None:
        """Fetch data from Silea waste pickup."""

        _LOGGER.info("Triggered calendar update")

        calendar = await self.get_calendar()
        next_services = self.get_next_service(calendar)

        for service, pickup_date in next_services.items():
            self._pickup.update({service: pickup_date})  # type: ignore

    async def next_pickup(self, waste_type: str) -> Optional[datetime]:
        """Return date of next pickup of the requested waste type."""
        return self._pickup.get(waste_type)

    async def close(self) -> None:
        """Close open client session."""
        if self._close_session:
            await self._session.close()

    async def __aenter__(self) -> "SileaWp":
        """Async enter."""
        return self

    async def __aexit__(self, *exc_info) -> None:
        """Async exit."""
        await self.close()
