"""Config flow to configure the Giphy integration."""
import logging

import voluptuous as vol

from homeassistant import config_entries
from .const import DOMAIN
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_API_KEY, CONF_ID, CONF_MAXIMUM
from homeassistant.helpers.aiohttp_client import async_get_clientsession

import homeassistant.helpers.config_validation as cv

from hashlib import sha256

_LOGGER = logging.getLogger(__name__)


@config_entries.HANDLERS.register(DOMAIN)
class GiphyFlowHandler(ConfigFlow):
    """Handle a Giphy config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def _show_setup_form(self, errors=None):
        """Show the setup form to the user."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): str,
                    #  vol.Optional(CONF_MAXIMUM, default=10): cv.positive_int,
                }
            ),
            errors=errors or {},
        )

    async def async_step_user(self, user_input=None):
        """Handle a flow initiated by the user."""
        if user_input is None:
            return await self._show_setup_form(user_input)

        api_key = user_input[CONF_API_KEY]

        hash = sha256(api_key.encode('utf-8')).hexdigest()[-7:]

        return self.async_create_entry(
            title=f"Client {hash}",
            data={
                CONF_ID: hash,
                CONF_API_KEY: api_key,
            },
        )
