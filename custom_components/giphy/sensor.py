"""Support for Giphy sensors."""
import logging
from typing import Any, Callable, Dict
from datetime import timedelta

from .const import DATA_UPDATE, DOMAIN, CONF_SEARCHES, CONF_SEARCH_TERM

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_ID, CONF_NAME
from homeassistant.core import callback
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import HomeAssistantType

from .giphy import GiphyClient
from random import choice

ATTR_IMAGES = "images"

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(hours=12)
PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistantType, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up Giphy sensor based on a config entry."""

    _LOGGER.info('Setup giphy sensor "%s"', entry.data[CONF_ID])
    _LOGGER.info('Setup giphy sensor with conf "%s"', entry.data)
    client: GiphyClient = hass.data[DOMAIN][entry.data[CONF_ID]]

    sensors = [
        GiphySensor(
            client, 
            unique_id=entry.data[CONF_ID], 
            name="giphy_trending",
            updater=lambda client: client.trending()
        ),
    ]

    additional_searches = entry.data[CONF_SEARCHES]
    for conf in additional_searches:
        term = conf.get(CONF_SEARCH_TERM)
        sensors.append(
            GiphySensor(
                client, 
                unique_id=entry.data[CONF_ID], 
                name=f"giphy_{conf.get(CONF_NAME, conf.get(CONF_SEARCH_TERM))}",
                updater=lambda client, t=term: client.search(t)
            )
        )

    async_add_entities(sensors, True)


class GiphySensor(Entity):
    """Defines a Giphy sensor."""

    def __init__(
        self, 
        client: GiphyClient,
        name: str,
        unique_id: str,
        updater: Callable
    ) -> None:
        """Initialize the Giphy entity."""
        self._unique_id = unique_id
        self._name = name
        self.client = client
        self._unsub_dispatcher = None

        self._images = []
        self._state = None
        self._updater = updater


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
        return choice(self._images).get("url") if self._images else None

    async def async_update(self) -> None:
        """Update Giphy entity."""
        self._images = await self._updater(self.client)

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information about Giphy."""
        return {
            "identifiers": {(DOMAIN, self._unique_id)},
            "name": "Giphy",
            "manufacturer": "Giphy",
        }