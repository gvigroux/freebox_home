"""Represent the Freebox router and its devices and sensors."""
from datetime import datetime, timedelta
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from freebox_api import Freepybox
from freebox_api.exceptions import HttpRequestError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.util import slugify

from .const import (
    API_VERSION,
    APP_DESC,
    DOMAIN,
    STORAGE_KEY,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)


class FreeboxRouter:
    """Representation of a Freebox router."""

    def __init__(self, hass: HomeAssistantType, entry: ConfigEntry) -> None:
        """Initialize a Freebox router."""
        self.hass = hass
        self._entry = entry
        self._host = entry.data[CONF_HOST]
        self._port = entry.data[CONF_PORT]

        self._api: Freepybox = None
        self._name = None
        self.mac = None
        self._sw_v = None
        self._attrs = {}

        self.nodes: Dict[str, Any] = {}

        self._unsub_dispatcher = None
        self.listeners = []

    async def setup(self) -> None:
        """Set up a Freebox router."""
        self._api = await get_api(self.hass, self._host)

        try:
            await self._api.open(self._host, self._port)
        except HttpRequestError:
            _LOGGER.exception("Failed to connect to Freebox")
            return ConfigEntryNotReady

        # System
        fbx_config = await self._api.system.get_config()
        self.mac   = "FbxHome_" + fbx_config["mac"]
        self._name = fbx_config["model_info"]["pretty_name"]
        self._sw_v = fbx_config["firmware_version"]

        # Devices & sensors
        await self.update_all()
        self._unsub_dispatcher = async_track_time_interval(self.hass, self.update_all, SCAN_INTERVAL)

    async def update_all(self, now: Optional[datetime] = None) -> None:
        """Update all Freebox platforms."""
        await self.update_nodes()
        
    async def update_nodes(self) -> None:
        """Update Freebox Nodes"""
        new_device = False
        fbx_nodes: Dict[str, Any] = await self._api.home.get_home_nodes()
        #_LOGGER.warning(fbx_nodes)

        for fbx_node in fbx_nodes:
            node_id = fbx_node["id"]
            if self.nodes.get(node_id) is None:
                new_device = True
            self.nodes[node_id] = fbx_node

        #async_dispatcher_send(self.hass, self.signal_device_update)

        if new_device:
            async_dispatcher_send(self.hass, self.signal_device_new)

    async def close(self) -> None:
        """Close the connection."""
        if self._api is not None:
            await self._api.close()
            self._unsub_dispatcher()
        self._api = None

    @property
    def signal_device_new(self) -> str:
        """Event specific per Freebox entry to signal new device."""
        return f"{DOMAIN}-{self._host}-device-new"


async def get_api(hass: HomeAssistantType, host: str) -> Freepybox:
    """Get the Freebox API."""
    freebox_path = Path(hass.helpers.storage.Store(STORAGE_VERSION, STORAGE_KEY).path)
    freebox_path.mkdir(exist_ok=True)
    token_file = Path(f"{freebox_path}/{slugify(host)}.conf")

    return Freepybox(APP_DESC, token_file, API_VERSION)
