import logging
from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

"""Support for rollerShutterIoT Covers"""

CONF_UNIQUE_ID = 'unique_id'


_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Activate component."""
    _LOGGER.debug("Wait for MQTT integration client to become available..");
    # Make sure MQTT integration is enabled and the client is available
    if not await mqtt.async_wait_for_mqtt_client(hass):
        _LOGGER.error("MQTT integration is not available yet")
        return False
    _LOGGER.debug("MQTT integration is ready now, activate rollerShutterIoT component");
    return True