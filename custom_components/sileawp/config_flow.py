"""Config flow to configure the Silea waste pickup integration."""
import logging

from .sileawp import (
    SileaWp,
    SileaWpAddressError,
    SileaWpConnectionError,
)
import voluptuous as vol

from homeassistant import config_entries
from .const import (
    CONF_CLIENT_ID,
    CONF_STREET_ID,
    DOMAIN
)
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_ID
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)


@config_entries.HANDLERS.register(DOMAIN)
class SileaWpFlowHandler(ConfigFlow):
    """Handle a Silea waste pickup config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def _show_setup_form(self, errors=None):
        """Show the setup form to the user."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CLIENT_ID): str,
                    vol.Required(CONF_STREET_ID): str
                }
            ),
            errors=errors or {},
        )

    async def async_step_user(self, user_input=None):
        """Handle a flow initiated by the user."""
        if user_input is None:
            return await self._show_setup_form(user_input)

        errors = {}

        session = async_get_clientsession(self.hass)

        sileawp = SileaWp(
            client_id=user_input[CONF_CLIENT_ID],
            street_id=user_input[CONF_STREET_ID],
            session=session,
        )

        unique_id = sileawp.unique_id()

        entries = self._async_current_entries()
        for entry in entries:
            if entry.data[CONF_ID] == unique_id:
                return self.async_abort(reason="address_already_set_up")

        return self.async_create_entry(
            title=unique_id,
            data={
                CONF_ID: unique_id,
                CONF_CLIENT_ID: user_input[CONF_CLIENT_ID],
                CONF_STREET_ID: user_input[CONF_STREET_ID],
            },
        )