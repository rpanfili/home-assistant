# -*- coding: utf-8 -*-
"""Asynchronous Python client for the Silea waste pickup API."""
import asyncio
import json
import socket
from datetime import datetime, timedelta, date
from typing import Dict, Optional

import aiohttp
import async_timeout
from yarl import URL

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

    async def _request(self, uri: str, method: str = "POST", data=None):
        """Handle a request to Silea waste pickup."""

        url = URL.build(
            scheme="https", host=API_HOST, port=443, path=API_BASE_URI
        ).join(URL(uri))

        headers = {
            "user-agent": self.user_agent,
            "origin": "https://www.sileaspa.it",
            "authority": "www.sileaspa.it",
            "referer": "https://www.sileaspa.it/servizi/servizi-ai-cittadini/giorni-orari-raccolta/",
        }

        import urllib.parse

        raw_data = {
            **{
                "action": "get_calendar",
                "id_cliente": self.client_id,
                "id_via": self.street_id,
                "id_mese": 9,  # todo!
            },
            **(data or {}),
        }

        try:
            with async_timeout.timeout(self.request_timeout):
                response = await self._session.request(
                    method,
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

        calendar = await self._request("getCalendario/")

        services = {}
        now = datetime.now()

        for pickup in calendar:
            service = API_TO_SERVICE.get(pickup["TipologiaServizio"])

            if service is None:
                continue

            pickup_date = None
            if pickup["Data"]:
                pickup_date = datetime.strptime(pickup["Data"], "%Y-%m-%dT%H:%M:%S")

                if pickup_date < now:
                    continue

                services[service] = (
                    pickup_date
                    if (
                        services.get(service) is None or pickup_date < services[service]
                    )
                    else services[service]
                )

        for service, pickup_date in services.items():
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
