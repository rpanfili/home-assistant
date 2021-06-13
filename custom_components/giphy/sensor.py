"""Support for Giphy sensors."""
import logging
from typing import Any, Dict
from datetime import timedelta

from .const import DATA_UPDATE, DOMAIN

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_ID
from homeassistant.core import callback
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import HomeAssistantType

from .giphy import GiphyClient
from random import choice

ATTR_IMAGES = "images"

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(hours=1)
PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistantType, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up Giphy sensor based on a config entry."""

    _LOGGER.info('Setup giphy sensor "%s"', entry.data[CONF_ID])
    client: GiphyClient = hass.data[DOMAIN][entry.data[CONF_ID]]

    sensors = [
        GiphySensor(client, unique_id=entry.data[CONF_ID], name="giphy_trending"),
    ]

    async_add_entities(sensors, True)


class GiphySensor(Entity):
    """Defines a Giphy sensor."""

    def __init__(
        self, 
        client: GiphyClient,
        name: str,
        unique_id: str
    ) -> None:
        """Initialize the Giphy entity."""
        self._unique_id = unique_id
        self._name = name
        self._client = client
        self._unsub_dispatcher = None

        self._images = []
        self._state = None


    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def icon(self) -> str:
        """Return the mdi icon of the entity."""
        return "mdi:gif"

    @property
    def should_poll(self) -> bool:
        """Return the polling requirement of the entity."""
        return True

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            ATTR_IMAGES: self._images
        }

    async def async_added_to_hass(self) -> None:
        """Connect to dispatcher listening for entity data notifications."""
        self._unsub_dispatcher = async_dispatcher_connect(
            self.hass, DATA_UPDATE, self._schedule_immediate_update
        )

    async def async_will_remove_from_hass(self) -> None:
        """Disconnect from update signal."""
        self._unsub_dispatcher()

    @callback
    def _schedule_immediate_update(self, unique_id: str) -> None:
        """Schedule an immediate update of the entity."""
        if unique_id == self._unique_id:
            self.async_schedule_update_ha_state(True)

    @property
    def state(self):
        """Return an image from cache"""
        return choice(self._images).get("mp4")

    async def async_update(self) -> None:
        """Update Giphy entity."""
        self._images = await self._client.trending()

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information about Giphy."""
        return {
            "identifiers": {(DOMAIN, self._unique_id)},
            "name": "Giphy",
            "manufacturer": "Giphy",
        }