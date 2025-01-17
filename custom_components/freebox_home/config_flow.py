"""Config flow to configure the Freebox integration."""
import logging

from freebox_api.exceptions import AuthorizationError, HttpRequestError, InsufficientPermissionsError
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import AbortFlow

from .const import DOMAIN
from .router import get_api

_LOGGER = logging.getLogger(__name__)

class FreeboxFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        """Initialize Freebox config flow."""
        self._host = None
        self._port = None

    def _show_setup_form(self, user_input=None, errors=None):
        """Show the setup form to the user."""

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=""): str,
                    vol.Required(CONF_PORT, default=""): int,
                }
            ),
            errors=errors or {},
        )


    async def async_step_user(self, user_input=None):
        """Handle a flow initiated by the user."""
        errors = {}
        if user_input is None:
            return self._show_setup_form(user_input, errors)

        self._host = user_input[CONF_HOST]
        self._port = user_input[CONF_PORT]

        # Check if already configured
        await self.async_set_unique_id(self._host + "_freebox_home")
        self._abort_if_unique_id_configured()

        return await self.async_step_link()


    async def async_step_unignore(self, user_input):
        raise AbortFlow("Nothing to do?")


    async def async_step_link(self, user_input=None):
        """Attempt to link with the Freebox router.

        Given a configured host, will ask the user to press the button
        to connect to the router.
        """
        if user_input is None:
            return self.async_show_form(step_id="link")

        errors = {}
        
        try:
            # Open connection, check authentication and permissions
            fbx = await get_api(self.hass, self._host, self._port)
            
            # Wait
            await fbx.system.get_config()
            await self.hass.async_block_till_done()

            # Close connection
            await fbx.close()

            return self.async_show_form(step_id="permission")
            '''
            return self.async_create_entry(
                title=self._host,
                data={CONF_HOST: self._host, CONF_PORT: self._port},
            )
            '''

        except AuthorizationError as error:
            _LOGGER.error("AuthorizationError: %s", error)
            errors["base"] = "register_failed"

        except HttpRequestError:
            _LOGGER.error("Error connecting to the Freebox router at %s", self._host)
            errors["base"] = "cannot_connect"

        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unknown error connecting with Freebox router at %s", self._host)
            errors["base"] = "unknown"
        return self.async_show_form(step_id="link", errors=errors)



    # Ask for HOME permission
    async def async_step_permission(self, user_input=None):
        errors = {}
        try:
            fbx = await get_api(self.hass, self._host, self._port)
            await fbx.home.get_home_nodes()

            return self.async_create_entry(
                title=self._host,
                data={CONF_HOST: self._host, CONF_PORT: self._port},
            )

        except InsufficientPermissionsError as error:
            _LOGGER.error(error)
            errors["base"] = "unknown"

        except Exception:
            _LOGGER.exception("Unknown error connecting with Freebox router at %s", self._host)
            errors["base"] = "unknown"
        finally: 
            await fbx.close()

        return self.async_show_form(step_id="permission", errors=errors)


    async def async_step_import(self, user_input=None):
        """Import a config entry."""
        return await self.async_step_user(user_input)


    async def async_step_zeroconf(self, discovery_info):
        """Initialize step from zeroconf discovery."""
        if( discovery_info.properties.get('device_type', None) == None):
            raise AbortFlow("Invalid discovery info")
        if( not discovery_info.properties.get('device_type').startswith("FreeboxServer7") ):
            raise AbortFlow("Invalid Freebox discovered. This Addon is only working with the Freebox Delta")
        self._host = discovery_info.properties.get('api_domain', None)
        self._port = discovery_info.properties.get('https_port', None)
        if(self._host == None or self._port == None):
            raise AbortFlow("Invalid discovery info (missing domain or port)")
        return await self.async_step_user({CONF_HOST: self._host, CONF_PORT: self._port})
