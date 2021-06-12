# -*- coding: utf-8 -*-
# pylint: disable=W0621
"""Asynchronous Python client for the Giphy API."""

import asyncio

from giphy.client import (  # noqa
    GiphyClient
)

GIPHY_API_KEY="*******"

async def main(loop):
    """Show example on stats from Giphy."""
    async with GiphyClient(api_key=GIPHY_API_KEY, loop=loop) as giphy:
        images = await giphy.trending()
        for image in images:
            print(image)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop))