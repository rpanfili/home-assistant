# -*- coding: utf-8 -*-
"""Asynchronous Python client for the Giphy API."""
import asyncio
import json
import socket
from datetime import datetime, timedelta, date
from typing import Dict, Optional
from hashlib import sha256
import urllib.parse as urlparse
from urllib.parse import ParseResult, parse_qsl, unquote, urlencode, urlsplit, quote

import aiohttp
import async_timeout
from yarl import URL

from .__version__ import __version__
from .const import API_BASE_URI, API_HOST
from .exceptions import (
    GiphyAddressError,
    GiphyConnectionError,
    GiphyError,
)

import logging

_LOGGER = logging.getLogger(__name__)


class GiphyClient:
    """Main class for handling connections with Giphy."""

    def __init__(
        self,
        api_key: str,
        loop=None,
        request_timeout: int = 10,
        session=None,
        user_agent: str = None,
    ):
        """Initialize connection with Giphy."""
        self._loop = loop
        self._session = session
        self._close_session = False

        self.api_key = api_key

        self.request_timeout = request_timeout
        self.user_agent = user_agent

        self._pickup = {}  # type: Dict[str, datetime]

        if self._loop is None:
            self._loop = asyncio.get_event_loop()

        if self._session is None:
            self._session = aiohttp.ClientSession(loop=self._loop)
            self._close_session = True

        if self.user_agent is None:
            self.user_agent = "GiphyClient/{}".format(__version__)

    async def _request(self, uri: str, method: str = "GET", data=None):
        """Handle a request to Giphy."""

        url = URL.build(
            scheme="https", host=API_HOST, port=443, path=API_BASE_URI
        ).join(URL(uri))

        params = {"api_key": self.api_key}
        url = url.update_query(params)

        headers = {"user-agent": self.user_agent, "Accept": "application/json"}

        raw_data = data or {}

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
            raise GiphyConnectionError(
                "Timeout occurred while connecting to Giphy API."
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            raise GiphyConnectionError(
                "Error occurred while communicating with Giphy."
            ) from exception

        content_type = response.headers.get("Content-Type", "")
        if (response.status // 100) in [4, 5]:
            contents = await response.read()
            response.close()

            if content_type == "application/json":
                raise GiphyError(response.status, json.loads(contents.decode("utf8")))
            raise GiphyError(response.status, {"message": contents.decode("utf8")})

        if "application/json" in response.headers["Content-Type"]:
            return await response.json()
        return await response.text()

    def unique_id(self) -> Optional[str]:
        """Return unique address ID."""
        if self._unique_id is None:
            self._unique_id = f"IDCliente={self.client_id}|IDVia={self.street_id}"
        return self._unique_id

    async def trending(self) -> None:
        """Fetch trending gifs."""

        _LOGGER.debug("Fetch trending")

        response_data = await self._request("/v1/gifs/trending?rating=r")

        images = [urls.get('original') for urls in [image.get('images') for image in response_data.get('data')]]

        return images

    async def search(self, term: str) -> None:
        """Search gifs."""

        _LOGGER.debug("Search for %s", term)

        response_data = await self._request(f"/v1/gifs/search?rating=r&q={quote(term)}")

        images = [urls.get('original') for urls in [image.get('images') for image in response_data.get('data')]]

        return images


    async def close(self) -> None:
        """Close open client session."""
        if self._close_session:
            await self._session.close()

    async def __aenter__(self) -> "Giphy":
        """Async enter."""
        return self

    async def __aexit__(self, *exc_info) -> None:
        """Async exit."""
        await self.close()