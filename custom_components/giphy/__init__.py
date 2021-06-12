"""Support for Giphy."""
import asyncio
from datetime import timedelta
import logging
from typing import Optional

import voluptuous as vol

from .const import (
    DATA_UPDATE,
    DOMAIN,
)
from .giphy import GiphyClient
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_ID
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType, HomeAssistantType

SCAN_INTERVAL = timedelta(hours=1)

_LOGGER = logging.getLogger(__name__)

SERVICE_UPDATE = "update"
SERVICE_SCHEMA = vol.Schema({vol.Optional(CONF_ID): cv.string})


async def _update_pic(hass: HomeAssistantType, unique_id: Optional[str]) -> None:
    """Update Giphy sensors."""

    data: dict = hass.data.get(DOMAIN, {})
    if len(data) < 1:
        _LOGGER.info("No sensors to update")
        return

    if unique_id is not None:
        entity = hass.data[DOMAIN].get(unique_id)
        if entity is not None:
            await entity.update()
            async_dispatcher_send(hass, DATA_UPDATE, unique_id)
    else:
        tasks = []
        for entity in hass.data[DOMAIN].values():
            tasks.append(entity.update())
        await asyncio.wait(tasks)

        for uid in hass.data[DOMAIN]:
            async_dispatcher_send(hass, DATA_UPDATE, uid)


async def async_setup(hass: HomeAssistantType, config: ConfigType) -> bool:
    """Set up the Giphy components."""
    hass.data.setdefault(DOMAIN, {})

    # async def update(call) -> None:
    #     """Service call to manually update the data."""
    #     unique_id = call.data.get(CONF_ID)
    #     await _update_pic(hass, unique_id)

    # hass.services.async_register(DOMAIN, SERVICE_UPDATE, update, schema=SERVICE_SCHEMA)

    return True


async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry) -> bool:
    """Set up Giphy from a config entry."""
    _LOGGER.info("Setup entry %s..", entry.data[CONF_ID])
    session = async_get_clientsession(hass)
    client = GiphyClient(
        api_key=entry.data[CONF_API_KEY],
        session=session,
    )

    unique_id = entry.data[CONF_ID]
    hass.data.setdefault(DOMAIN, {})[unique_id] = client

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )

    async def _interval_update(now=None) -> None:
        """Update calendar data."""
        await _update_pic(hass, unique_id)

    async_track_time_interval(hass, _interval_update, SCAN_INTERVAL)

    return True


async def async_unload_entry(hass: HomeAssistantType, entry: ConfigEntry) -> bool:
    """Unload config entry."""
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")

    del hass.data[DOMAIN][entry.data[CONF_ID]]

    return True