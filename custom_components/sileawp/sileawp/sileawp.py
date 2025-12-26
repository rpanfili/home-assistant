# -*- coding: utf-8 -*-
"""Asynchronous Python client for the Silea waste pickup API."""
import asyncio
import json
import socket
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from typing import Dict, List, Optional
from re import sub
from zoneinfo import ZoneInfo

import aiohttp
import async_timeout
from yarl import URL
from pydantic import ValidationError

from .__version__ import __version__
from .const import API_BASE_URI, API_HOST, API_TO_SERVICE, ServiceType
from .exceptions import (
    SileaWpAddressError,
    SileaWpConnectionError,
    SileaWpError,
)
from .models import PickupDay

import logging

_LOGGER = logging.getLogger(__name__)


class SileaWp:
    """Main class for handling connections with Silea waste pickup."""
    
    TIMEZONE = ZoneInfo("Europe/Rome")
    MAX_RETRIES = 3
    RETRY_BACKOFF_FACTOR = 2  # seconds

    def __init__(
        self,
        client_id: str,
        street_id: str,
        request_timeout: int = 10,
        session: Optional[aiohttp.ClientSession] = None,
        user_agent: Optional[str] = None,
    ):
        """Initialize connection with Silea waste pickup.
        
        Args:
            client_id: Client identifier for the Silea API.
            street_id: Street identifier for the address.
            request_timeout: Request timeout in seconds (default: 10).
            session: Optional aiohttp ClientSession to use.
            user_agent: Optional custom user agent string.
        """
        self._session = session
        self._own_session = session is None

        self.street_id = street_id
        self.client_id = client_id

        self.request_timeout = request_timeout
        self.user_agent = user_agent or f"SileaWpClient/{__version__}"

        self._unique_id: Optional[str] = None
        self._pickup: Dict[ServiceType, datetime] = {}
        self._last_update: Optional[datetime] = None
        self._calendar_data: List[Dict[str, datetime]] = []

        if self._session is None:
            self._session = aiohttp.ClientSession()
            self._own_session = True
    
    def __repr__(self) -> str:
        """Return string representation of the client."""
        return (
            f"SileaWp(client_id={self.client_id!r}, "
            f"street_id={self.street_id!r}, "
            f"timeout={self.request_timeout}s)"
        )

    def get_next_service(self, calendar: List[Dict[str, datetime]]) -> Dict[ServiceType, datetime]:
        """Calculate the next pickup date for each service type.
        
        Args:
            calendar: List of pickup dictionaries with 'service' and 'date' keys.
            
        Returns:
            Dictionary mapping service types to their next pickup datetime.
        """
        _LOGGER.debug("Calculating next services from calendar data")
        services: Dict[ServiceType, datetime] = {}
        now = datetime.now(self.TIMEZONE)
        
        for pickup in calendar:
            service_name: ServiceType = pickup["service"]
            service_date: datetime = pickup["date"]
            
            if service_date < now:
                continue

            # Update if this is the first occurrence or an earlier date for this service
            if service_name not in services or service_date < services[service_name]:
                services[service_name] = service_date

        return services

    async def get_calendars(self, months: int = 3) -> List[Dict[str, datetime]]:
        """Fetch and parse calendar data for the specified number of months.
        
        Args:
            months: Number of months to fetch (default: 3).
            
        Returns:
            List of pickup dictionaries with 'service' and 'date' keys.
            
        Raises:
            ValueError: If months parameter is invalid.
        """
        if months < 1:
            raise ValueError("months must be at least 1")
            
        _LOGGER.info("Fetching calendar from Silea waste pickup API for %d months", months)

        start_date = date.today()
        pickups = []

        for iteration in range(months):
            # Calculate the first day of the month, handling year rollover
            fetch_date = datetime(start_date.year, start_date.month, 1) + relativedelta(months=iteration)
            month_key = f"{fetch_date.month}_{fetch_date.year}"
            
            try:
                month_calendar = await self._get_calendar(month_key)
                if not month_calendar:
                    _LOGGER.warning("No calendar data returned for %s", month_key)
                    continue
                    
                if not isinstance(month_calendar, list):
                    _LOGGER.error("Invalid calendar data format for %s: expected list, got %s", 
                                month_key, type(month_calendar).__name__)
                    continue
                    
                pickups.extend(self._parse_calendar_days(month_calendar))
            except ValidationError as e:
                _LOGGER.error("Failed to parse calendar data for %s: %s", month_key, e)
                continue
            except Exception as e:
                _LOGGER.error("Unexpected error processing calendar for %s: %s", month_key, e)
                continue

        return pickups

    def _parse_calendar_days(self, calendar_data: List[dict]) -> List[Dict[str, datetime]]:
        """Parse raw calendar data into structured pickup information.
        
        Args:
            calendar_data: List of raw calendar day dictionaries from API.
            
        Returns:
            List of pickup dictionaries with normalized service names and dates (timezone-aware).
        """
        pickups = []
        
        for day_data in calendar_data:
            try:
                pickup_day = PickupDay(**day_data)
            except ValidationError as e:
                _LOGGER.warning("Failed to validate pickup day data: %s", e)
                continue
                
            # Get base date and make it timezone-aware
            base_date = pickup_day.pickup_date.replace(tzinfo=self.TIMEZONE)

            for service in pickup_day.services:
                service_type = service.service
                normalized_service: Optional[ServiceType] = API_TO_SERVICE.get(service_type)
                
                if normalized_service is None:
                    _LOGGER.warning("Unknown service type '%s', skipping", service_type)
                    continue

                # Extract pickup time from hours field (e.g., "05:30 - 13:30")
                try:
                    pickup_time_str = sub(r" -.+", "", service.hours)
                    pickup_time = datetime.strptime(pickup_time_str, "%H:%M")
                    pickup_date = base_date.replace(
                        hour=pickup_time.hour,
                        minute=pickup_time.minute,
                        second=0,
                        microsecond=0,
                    )
                except (ValueError, AttributeError) as e:
                    _LOGGER.warning(
                        "Failed to parse time from '%s': %s. Using base date.",
                        service.hours, e
                    )
                    pickup_date = base_date

                pickups.append({
                    "service": normalized_service,
                    "date": pickup_date,
                })
                _LOGGER.debug(
                    "Parsed pickup: %s on %s (notes: %s)",
                    normalized_service, pickup_date, service.notes
                )

        return pickups

    async def _get_calendar(self, month: str) -> List[dict]:
        """Fetch calendar data for a specific month from the API with retry logic.
        
        Args:
            month: Month identifier in format 'MM_YYYY' (e.g., '1_2026').
            
        Returns:
            List of raw calendar day dictionaries from the API.
            
        Raises:
            SileaWpConnectionError: If connection to the API fails after retries.
            SileaWpAddressError: If the address is not found (404).
            SileaWpError: If the API returns an error response.
        """
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

        last_exception = None
        
        # Retry logic with exponential backoff
        for attempt in range(self.MAX_RETRIES):
            try:
                if attempt > 0:
                    backoff_time = self.RETRY_BACKOFF_FACTOR ** attempt
                    _LOGGER.debug(
                        "Retrying request for month %s (attempt %d/%d) after %ds",
                        month, attempt + 1, self.MAX_RETRIES, backoff_time
                    )
                    await asyncio.sleep(backoff_time)
                
                _LOGGER.debug(
                    "Requesting calendar data from %s for month %s (attempt %d/%d)",
                    url, month, attempt + 1, self.MAX_RETRIES
                )

                async with async_timeout.timeout(self.request_timeout):
                    response = await self._session.request(
                        "POST",
                        url,
                        data=raw_data,
                        headers=headers,
                        ssl=True,
                    )
                
                # Handle response
                content_type = response.headers.get("Content-Type", "")
                if (response.status // 100) in [4, 5]:
                    contents = await response.read()
                    response.close()

                    # 404 typically indicates invalid client_id or street_id - don't retry
                    if response.status == 404:
                        raise SileaWpAddressError(
                            f"Address not found for month {month}: "
                            f"client_id={self.client_id}, street_id={self.street_id}"
                        )

                    error_msg = contents.decode("utf8")
                    if content_type == "application/json":
                        try:
                            error_data = json.loads(error_msg)
                        except json.JSONDecodeError:
                            error_data = {"message": error_msg}
                    else:
                        error_data = {"message": error_msg}
                    
                    raise SileaWpError(
                        response.status,
                        {
                            "error": error_data,
                            "month": month,
                            "url": str(url),
                            "status": response.status,
                        }
                    )

                if "application/json" in response.headers["Content-Type"]:
                    data = await response.json()
                    if isinstance(data, list):
                        return data
                    _LOGGER.warning(
                        "Unexpected response format for month %s: expected list, got %s",
                        month, type(data).__name__
                    )
                    return []
                
                # Fallback for non-JSON responses
                text = await response.text()
                _LOGGER.warning(
                    "Received non-JSON response for month %s: %s",
                    month, text[:200]
                )
                return []
                
            except asyncio.TimeoutError as exception:
                last_exception = SileaWpConnectionError(
                    f"Timeout after {self.request_timeout}s connecting to Silea API "
                    f"for month {month} (attempt {attempt + 1}/{self.MAX_RETRIES}): {url}"
                )
                if attempt == self.MAX_RETRIES - 1:
                    raise last_exception from exception
                continue
                
            except (aiohttp.ClientError, socket.gaierror) as exception:
                last_exception = SileaWpConnectionError(
                    f"Connection error for month {month} "
                    f"(attempt {attempt + 1}/{self.MAX_RETRIES}): {type(exception).__name__} - {exception}"
                )
                if attempt == self.MAX_RETRIES - 1:
                    raise last_exception from exception
                continue
            
            except SileaWpAddressError:
                # Don't retry on address errors
                raise
            
            except SileaWpError:
                # Don't retry on API errors (4xx/5xx)
                raise
        
        # Should not reach here, but just in case
        if last_exception:
            raise last_exception
        return []

    def unique_id(self) -> Optional[str]:
        """Return unique address ID."""
        if self._unique_id is None:
            self._unique_id = f"IDCliente={self.client_id}|IDVia={self.street_id}"
        return self._unique_id

    async def update(self, months: int = 3) -> None:
        """Fetch data from Silea waste pickup.
        
        Args:
            months: Number of months to fetch (default: 3).
        """
        _LOGGER.info("Triggered calendar update")

        calendar = await self.get_calendars(months=months)
        next_services = self.get_next_service(calendar)

        self._pickup = next_services
        self._calendar_data = calendar
        self._last_update = datetime.now(self.TIMEZONE)

    async def next_pickup(self, waste_type: ServiceType) -> Optional[datetime]:
        """Return date of next pickup of the requested waste type.
        
        Args:
            waste_type: The service type to query.
            
        Returns:
            Timezone-aware datetime of next pickup, or None if not found.
        """
        return self._pickup.get(waste_type)

    async def close(self) -> None:
        """Close open client session safely.
        
        Note: Only closes the session if it was created by this instance.
        If a session was provided to __init__, it won't be closed here.
        """
        if self._own_session and self._session is not None:
            try:
                if not self._session.closed:
                    await self._session.close()
                    _LOGGER.debug("Session closed successfully")
            except Exception as e:
                _LOGGER.warning("Error closing session: %s", e)

    async def __aenter__(self) -> "SileaWp":
        """Async enter."""
        return self

    async def __aexit__(self, *exc_info) -> None:
        """Async exit - ensures cleanup even on exception.
        
        Note: Only closes the session if it was created by this instance.
        Injected sessions are not closed and remain the caller's responsibility.
        """
        try:
            await self.close()
        except Exception as e:
            # Log but don't suppress the original exception
            _LOGGER.error("Error during context manager cleanup: %s", e)
