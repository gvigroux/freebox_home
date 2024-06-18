"""Support for Freebox devices (Freebox v6 and Freebox mini 4K)."""
import asyncio
import logging
import voluptuous as vol

from homeassistant.config_entries import SOURCE_DISCOVERY, ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, EVENT_HOMEASSISTANT_STOP
from homeassistant.helpers import config_validation as cv, discovery
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .router import FreeboxRouter

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass, config):
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Freebox component."""
    router = FreeboxRouter(hass, entry)
    await router.setup()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.unique_id] = router

    for platform in PLATFORMS:
        hass.async_create_task(hass.config_entries.async_forward_entry_setup(entry, platform))

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
        await router.close()

    return unload_ok
