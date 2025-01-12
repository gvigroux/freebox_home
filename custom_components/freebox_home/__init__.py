"""Support for Freebox devices (Freebox v6 and Freebox mini 4K)."""
import asyncio
import logging
import voluptuous as vol

from homeassistant.config_entries import SOURCE_DISCOVERY, ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, EVENT_HOMEASSISTANT_STOP
from homeassistant.helpers import config_validation as cv, discovery
from homeassistant.core import HomeAssistant

from freebox_api.exceptions import AuthorizationError, HttpRequestError

from .const import DOMAIN, PLATFORMS
from .router import (FreeboxRouter, get_api, remove_config)

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass, config):
    return True


async def blocking_calls(hass, api, entry):
    await api.open(entry.data[CONF_HOST], entry.data[CONF_PORT])

    fbx_config = await api.system.get_config()
    router = FreeboxRouter(hass, entry, api, fbx_config)
    await router.update_all()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.unique_id] = router
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

async def test(hass, api, entry):
    await api.open(entry.data[CONF_HOST], entry.data[CONF_PORT])


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Freebox component."""

    router = None
    try:
        api = await get_api(hass, entry.data[CONF_HOST], entry.data[CONF_PORT])
        fbx_config = await api.system.get_config()
        #await hass.async_add_executor_job(blocking_calls, hass, api, entry)
    except:
        _LOGGER.error("Unable to connect to the Freebox")

    router = FreeboxRouter(hass, entry, api, fbx_config)
    await router.update_all()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.unique_id] = router

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def async_close_connection(event):
        """Close Freebox connection on HA Stop."""
        await router.close()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, async_close_connection)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
            ]
        )
    )
    if unload_ok:
        router = hass.data[DOMAIN].pop(entry.unique_id)
        # No need to remove the old file because I will clean when we recreate the entry again (and no need to get a new credential if it's working)
        #await remove_config(hass, entry.data[CONF_HOST])
        await router.close()

    return unload_ok
