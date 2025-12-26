# -*- coding: utf-8 -*-
# pylint: disable=W0621
"""Asynchronous Python client for the Silea waste pickup API."""

import asyncio
import logging

logging.basicConfig(level=logging.DEBUG)

from .const import (  # noqa
    ServiceType,
    # Backward compatibility
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


async def main():
    """Show example on stats from SileaWp Milieu."""
    async with SileaWp(client_id="C563", street_id="001439") as tw:
        print(f"Client: {tw!r}")
        await tw.update()
        pickup = await tw.next_pickup(ServiceType.ORGANIC)
        print("Next pickup for Organic:", pickup)
        pickup = await tw.next_pickup(ServiceType.PLASTIC)
        print("Next pickup for Plastic:", pickup)
        pickup = await tw.next_pickup(ServiceType.PAPER)
        print("Next pickup for Paper:", pickup)
        pickup = await tw.next_pickup(ServiceType.NON_RECYCLABLE)
        print("Next pickup for Non-recyclable:", pickup)
        pickup = await tw.next_pickup(ServiceType.STREET_CLEAN)
        print("Next street clean up:", pickup)


if __name__ == "__main__":
    asyncio.run(main())
