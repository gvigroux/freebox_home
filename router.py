"""Represent the Freebox router and its devices and sensors."""
from datetime import datetime, timedelta
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from freebox_api import Freepybox
from freebox_api.exceptions import HttpRequestError

from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import slugify
from homeassistant.helpers.storage import Store

from .const import APP_DESC, DOMAIN, STORAGE_KEY, STORAGE_VERSION, API_VERSION

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=30)

class FreeboxRouter:
    """Representation of a Freebox router."""

    def __init__(self, hass, entry) -> None:
        """Initialize a Freebox router."""
        self.hass = hass
        self._host = entry.data[CONF_HOST]
        self._port = entry.data[CONF_PORT]
        self._api: Freepybox = None
        self.mac = None

        self.nodes: Dict[str, Any] = {}
        self._unsub_dispatcher = None

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

        # Devices & sensors
        await self.update_all()
        self._unsub_dispatcher = async_track_time_interval(self.hass, self.update_all, SCAN_INTERVAL)

    async def update_all(self, now: Optional[datetime] = None) -> None:
        """Update all nodes"""
        fbx_nodes: Dict[str, Any] = await self._api.home.get_home_nodes()
        for fbx_node in fbx_nodes:
            if( fbx_node["category"] not in ["pir","camera","alarm","dws","kfb","basic_shutter","shutter"] ):
                _LOGGER.warning("Node not supported: \n" +str(fbx_node))
                continue
            self.nodes[fbx_node["id"]] = fbx_node


    async def close(self) -> None:
        """Close the connection."""
        if self._api is not None:
            await self._api.close()
            self._unsub_dispatcher()
        self._api = None


async def get_api(hass, host: str) -> Freepybox:
    """Get the Freebox API."""
    #freebox_path = Path(hass.helpers.storage.Store(STORAGE_VERSION, STORAGE_KEY).path)
    freebox_path = Path(Store(hass, STORAGE_VERSION, STORAGE_KEY).path)
    freebox_path.mkdir(exist_ok=True)

    token_file = Path(f"{freebox_path}/{slugify(host)}.conf")
    return Freepybox(APP_DESC, token_file, API_VERSION)
