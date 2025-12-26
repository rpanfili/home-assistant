# -*- coding: utf-8 -*-
# pylint: disable=W0621
"""Asynchronous Python client for the Silea waste pickup API."""

import asyncio
import logging

logging.basicConfig(level=logging.DEBUG)

from .const import (  # noqa
    WASTE_TYPE_NON_RECYCLABLE,
    WASTE_TYPE_ORGANIC,
    WASTE_TYPE_PAPER,
    WASTE_TYPE_PLASTIC,
    STREET_CLEAN,
)
from .sileawp import (  # noqa
    SileaWp,
    SileaWpAddressError,
    SileaWpConnectionError,
    SileaWpError,
)


async def main(loop):
    """Show example on stats from SileaWp Milieu."""
    async with SileaWp(client_id="C563", street_id="001439", loop=loop) as tw:
        await tw.update()
        pickup = await tw.next_pickup(WASTE_TYPE_ORGANIC)
        print("Next pickup for Organic:", pickup)
        pickup = await tw.next_pickup(WASTE_TYPE_PLASTIC)
        print("Next pickup for Plastic:", pickup)
        pickup = await tw.next_pickup(WASTE_TYPE_PAPER)
        print("Next pickup for Paper:", pickup)
        pickup = await tw.next_pickup(WASTE_TYPE_NON_RECYCLABLE)
        print("Next pickup for Non-recyclable:", pickup)
        pickup = await tw.next_pickup(STREET_CLEAN)
        print("Next street clean up:", pickup)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop))
