"""Config flow to configure the Giphy integration."""
import logging
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant import config_entries
from .const import DOMAIN, CONF_SEARCHES, CONF_SEARCH_TERM, CONF_ADD_ANOTHER, CONF_SKIP_STEP
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_API_KEY, CONF_ID, CONF_NAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

import homeassistant.helpers.config_validation as cv

from hashlib import sha256

_LOGGER = logging.getLogger(__name__)


AUTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
    }
)
SEARCH_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(CONF_SEARCH_TERM): cv.string,
        vol.Optional(CONF_ADD_ANOTHER): cv.boolean,
        vol.Optional(CONF_SKIP_STEP): cv.boolean,
    }
)

async def validate_search(term: Optional[str], name: Optional[str], skip: bool) -> None:
    """Validates a search configuration."""

    if(name is not None and (term is None or term == '') and not skip):
        raise ValueError     

@config_entries.HANDLERS.register(DOMAIN)
class GiphyFlowHandler(ConfigFlow):
    """Handle a Giphy config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL


    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle a flow initiated by the user."""
        errors: Dict[str, str] = {}
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=AUTH_SCHEMA,
                errors=errors,
            )

        self.data = user_input
        
        api_key = user_input.get(CONF_API_KEY)
        hash = sha256(api_key.encode('utf-8')).hexdigest()[-7:]
        self.data[CONF_ID] = hash

        self.data[CONF_SEARCHES] = []
        return await self.async_step_search()

    async def async_step_search(self, user_input: Optional[Dict[str, Any]] = None):
        """Setup additional searches to track."""
        errors: Dict[str, str] = {}
        if user_input is not None:
            try:
                await validate_search(
                    user_input.get(CONF_SEARCH_TERM, None),
                    user_input.get(CONF_NAME, None),
                    user_input.get(CONF_SKIP_STEP, False)
                )
            except ValueError:
                errors["base"] = "invalid_search"          

            if not errors:
                skip = user_input.get(CONF_SKIP_STEP, False)
                term = user_input.get(CONF_SEARCH_TERM)
                if not skip and term is not None:
                    self.data[CONF_SEARCHES].append(
                        {
                            CONF_SEARCH_TERM: term,
                            CONF_NAME: user_input.get(CONF_NAME,term)
                        }
                    )  

                if user_input.get("add_another", False):
                    return await self.async_step_search()

                # Create the config entry.
                return self.async_create_entry(
                    title=f"Client {self.data[CONF_ID]}",
                    data=self.data
                )

        return self.async_show_form(
                step_id="search",
                data_schema=SEARCH_SCHEMA,
                errors=errors,
            )
        

           