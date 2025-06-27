"""Support for Silea waste pickup."""
import asyncio
from datetime import timedelta
import logging
from typing import Optional

from .sileawp import SileaWp
import voluptuous as vol

from .const import (
    CONF_CLIENT_ID,
    CONF_STREET_ID,
    DATA_UPDATE,
    DOMAIN,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ID, Platform
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType, HomeAssistantType

SCAN_INTERVAL = timedelta(days=1)

_LOGGER = logging.getLogger(__name__)

SERVICE_UPDATE = "update"
SERVICE_SCHEMA = vol.Schema({vol.Optional(CONF_ID): cv.string})

PLATFORMS: list[Platform] = [Platform.SENSOR]

async def _update_calendar(
    hass: HomeAssistantType, unique_id: Optional[str]
) -> None:
    """Update Silea waste pickup calendar."""
    
    data: dict = hass.data.get(DOMAIN,{})
    if len(data) < 1:
        _LOGGER.info("No sensors to update")
        return
    
    if unique_id is not None:
        calendar = hass.data[DOMAIN].get(unique_id)
        if calendar is not None:
            await calendar.update()
            async_dispatcher_send(hass, DATA_UPDATE, unique_id)
    else:
        tasks = []
        for calendar in hass.data[DOMAIN].values():
            tasks.append(calendar.update())
        await asyncio.wait(tasks)

        for uid in hass.data[DOMAIN]:
            async_dispatcher_send(hass, DATA_UPDATE, uid)


async def async_setup(hass: HomeAssistantType, config: ConfigType) -> bool:
    """Set up the Silea waste pickup components."""
    hass.data.setdefault(DOMAIN, {})

    async def update(call) -> None:
        """Service call to manually update the data."""
        unique_id = call.data.get(CONF_ID)
        await _update_calendar(hass, unique_id)

    hass.services.async_register(DOMAIN, SERVICE_UPDATE, update, schema=SERVICE_SCHEMA)

    return True


async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry) -> bool:
    """Set up Silea waste pickup from a config entry."""
    _LOGGER.info("Setup entry %s..", entry.data[CONF_ID])
    session = async_get_clientsession(hass)
    sileawp = SileaWp(
        client_id=entry.data[CONF_CLIENT_ID],
        street_id=entry.data[CONF_STREET_ID],
        session=session,
    )

    unique_id = entry.data[CONF_ID]
    hass.data.setdefault(DOMAIN, {})[unique_id] = sileawp

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    )

    async def _interval_update(now=None) -> None:
        """Update calendar data."""
        await _update_calendar(hass, unique_id)

    async_track_time_interval(hass, _interval_update, SCAN_INTERVAL)

    return True


async def async_unload_entry(hass: HomeAssistantType, entry: ConfigEntry) -> bool:
    """Unload config entry."""
    await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    del hass.data[DOMAIN][entry.data[CONF_ID]]

    return True