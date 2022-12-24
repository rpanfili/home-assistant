"""Support for RollerShutterIoT cover devices."""

import logging
import voluptuous as vol
from homeassistant.components import cover, mqtt
from homeassistant.core import HomeAssistant
from homeassistant.components.mqtt.cover import MqttCover, PLATFORM_SCHEMA, _PLATFORM_SCHEMA_BASE, PLATFORM_SCHEMA_MODERN
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType, HomeAssistantType
from homeassistant.const import (CONF_DEVICE, CONF_DEVICE_CLASS, CONF_NAME,
                                 CONF_OPTIMISTIC, CONF_VALUE_TEMPLATE,
                                 STATE_CLOSED, STATE_OPEN, STATE_UNKNOWN,
                                 STATE_ON)
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.event import async_track_state_change

from . import (CONF_UNIQUE_ID)

from homeassistant.components.cover import (ATTR_POSITION)

DOMAIN = 'cover'

_LOGGER = logging.getLogger(__name__)

CONF_POSITION_MIN = 'position_min'
CONF_POSITION_MIN_ENABLE = 'position_min_enable'
CONF_WINDOW_SENSOR = 'window_sensor'

EXTRA_SCHEMA = vol.Schema({
    vol.Optional(CONF_POSITION_MIN): cv.entity_id,
    vol.Optional(CONF_POSITION_MIN_ENABLE): cv.entity_id,
    vol.Optional(CONF_WINDOW_SENSOR): cv.entity_id
})

PLATFORM_SCHEMA = vol.All(
    cv.PLATFORM_SCHEMA.extend(
        _PLATFORM_SCHEMA_BASE.extend(
            EXTRA_SCHEMA.schema).schema),
)

async def async_setup_platform(hass: HomeAssistant,
                               config: ConfigType,
                               async_add_entities,
                               discovery_info=None):
    """Set up rIoT cover through configuration.yaml."""
    _LOGGER.debug("Setup rIoT cover with following config:");
    _LOGGER.debug(config)
    await _async_setup_entity(hass, config, async_add_entities)


async def _async_setup_entity(hass,
                              config,
                              async_add_entities,
                              config_entry=None,
                              discovery_data=None):
    """Set up the rIoT Cover."""
    async_add_entities(
        [RollerShutterIoTCover(hass, config, config_entry, discovery_data)])


class RollerShutterIoTCover(MqttCover, RestoreEntity):
    _position_min_id = None

    def __init__(self, hass, config, config_entry, discovery_data):
        """Initialize the cover."""
        _LOGGER.debug("RollerShutterIoT cover init..")
        super().__init__(hass, config, config_entry, discovery_data)
        self.hass = hass

    @property
    def position_min(self) -> int:
        """Return position min if enabled, zero otherwise"""
        position_min = 0
        if self.is_position_min_enabled:
            position_min_id = self._config.get(CONF_POSITION_MIN)
            if position_min_id:
                limit = self.hass.states.get(position_min_id)
                if limit is None:
                    _LOGGER.warning(
                        f"Entity is missing: {position_min_id} - (option: {CONF_POSITION_MIN}). Feature disabled"
                    )
                else:
                    position_min = limit.state
        return int(float(position_min))

    @property
    def is_position_min_enabled(self) -> bool:
        limit_enabled = True
        enabler_id = self._config.get(CONF_POSITION_MIN_ENABLE)
        if enabler_id is not None:
            enabler = self.hass.states.get(enabler_id)
            if enabler is None:
                _LOGGER.warning(
                    f"Entity is missing: {enabler_id} - (option: {CONF_POSITION_MIN_ENABLE}). Feature disabled"
                )
                limit_enabled = False
            else:
                limit_enabled = enabler.state == STATE_ON
                if limit_enabled:
                    # check also Window sensor, if exists
                    window_id = self._config.get(CONF_WINDOW_SENSOR)
                    if window_id:
                        window = self.hass.states.get(window_id)
                        if window is not None:
                            limit_enabled = window.state == STATE_ON
        return bool(limit_enabled)

    def is_position_safe(self, given_position: int) -> bool:
        """Return true if current position is safe, false otherwise"""
        _LOGGER.debug(
            f"IsPositionSafe | is min enabled: {self.is_position_min_enabled} - position min: {self.position_min} - given position: {given_position}"
        )
        return given_position is None or not self.is_position_min_enabled or self.position_min <= int(
            given_position)

    async def mqtt_async_added_to_hass(self):
        """Subscribe MQTT events."""
        await super().mqtt_async_added_to_hass()
        await self._async_init_listeners()

    async def _async_init_listeners(self):
        def register_listerner(config_field: str) -> bool:
            entity_id = self._config.get(config_field)
            if entity_id:
                _LOGGER.debug(
                    f"Register listener for {entity_id} entity changes")
                async_track_state_change(self.hass, entity_id,
                                         self._handle_position_changed)
            return entity_id is not None

        if register_listerner(CONF_POSITION_MIN_ENABLE):
            register_listerner(CONF_POSITION_MIN)
            register_listerner(CONF_WINDOW_SENSOR)

        # subscribe self state changes (for example on mqtt msg received)
        # async_track_state_change(
        #     self.hass, self.entity_id, self._handle_position_changed)

    async def _check_min_position(self):
        current_position = self.current_cover_position
        # updates current position only if needed

        if current_position is None:
            _LOGGER.warning(
                f"Unknown current position for \"{self.entity_id}\" cover")
            return

        if not self.is_position_safe(current_position):
            await self.async_set_cover_position(
                **{ATTR_POSITION: current_position})

    async def _handle_position_changed(self, entity_id, old_state, new_state):
        """Handle position_min_enable sensor changes."""
        if new_state is None:
            return
        await self._check_min_position()

    async def async_close_cover(self, **kwargs):
        await self.async_set_cover_position(
            **{ATTR_POSITION: self.position_min})

    async def async_set_cover_position(self, **kwargs):
        # if a position limit is set then limit down position to position_min
        if ATTR_POSITION in kwargs:
            given_position = kwargs[ATTR_POSITION]
            position_min = self.position_min
            _LOGGER.debug(
                f"SetCoverPosition | Position min: {position_min} - Given position: {given_position}"
            )
            if not self.is_position_safe(given_position):
                _LOGGER.debug(
                    f"Requested position below active position limit: {position_min} => override"
                )
                kwargs[ATTR_POSITION] = float(position_min)

        await super().async_set_cover_position(**kwargs)
