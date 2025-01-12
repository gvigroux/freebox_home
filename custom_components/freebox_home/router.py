"""Represent the Freebox router and its devices and sensors."""
from datetime import datetime, timedelta
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from freebox_api import Freepybox
from freebox_api.exceptions import AuthorizationError, HttpRequestError, InsufficientPermissionsError

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

    def __init__(self, hass, entry, api, fbx_config) -> None:
        """Initialize a Freebox router."""
        self.hass = hass
        self._host = entry.data[CONF_HOST]
        self._port = entry.data[CONF_PORT]
        self._api = api

        self.nodes: Dict[str, Any] = {}
        
        # System
        self.mac   = "FbxHome_" + fbx_config["mac"]

        # Devices & sensors
        self._unsub_dispatcher = async_track_time_interval(self.hass, self.update_all, SCAN_INTERVAL)



    #async def setup(self) -> None:
        #"""Set up a Freebox router."""
        #self._api = await get_api(self.hass, self._host)

        #await self.hass.async_add_executor_job(self.blocking_code)
        #try:
        #    #await self._api.open(self._host, self._port)
        #    result = await self.hass.async_add_executor_job(self._api.open,self._host, self._port)
        #except HttpRequestError:
        #    _LOGGER.exception("Failed to connect to Freebox")
        #    return ConfigEntryNotReady

        # System
        #fbx_config = await self._api.system.get_config()
        #self.mac   = "FbxHome_" + fbx_config["mac"]

        # Devices & sensors
        #await self.update_all()
        #self._unsub_dispatcher = async_track_time_interval(self.hass, self.update_all, SCAN_INTERVAL)

    async def update_all(self, now: Optional[datetime] = None) -> None:
        """Update all nodes"""
        try:
            fbx_nodes: Dict[str, Any] = await self._api.home.get_home_nodes()
        except InsufficientPermissionsError as error:
            _LOGGER.error("InsufficientPermissionsError: You need to browse http://mafreebox.freebox.fr/#Fbx.os.app.settings.Accounts and grant the access policy: \"Gestion de l'alarme et maison connectée\"")
            return

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


async def get_api(hass, host: str, port, retry = 0):
    """Get the Freebox API."""
    freebox_path = Store(hass, STORAGE_VERSION, STORAGE_KEY).path

    if not os.path.exists(freebox_path):
        await hass.async_add_executor_job(os.makedirs, freebox_path)

    token_file = Path(f"{freebox_path}/{slugify(host)}.conf")
    api = Freepybox(APP_DESC, token_file, api_version="latest")

    try:
        await api.open(host, port)
        await api.system.get_config()
    except AuthorizationError as error:
        _LOGGER.error("AuthorizationError: Please accept the application authorization on your Freebox screen")
        if( retry != 0 ):
            raise error
        await remove_config(hass, host)
        return await get_api(hass, host, port, 1)
    except InsufficientPermissionsError as error:
        _LOGGER.error("InsufficientPermissionsError: You need to browse http://mafreebox.freebox.fr/#Fbx.os.app.settings.Accounts and grant the access policy: \"Gestion de l'alarme et maison connectée\"")
        raise error

    return api


async def remove_config(hass, host: str):
    freebox_path = Store(hass, STORAGE_VERSION, STORAGE_KEY).path
    token_file = Path(f"{freebox_path}/{slugify(host)}.conf")
    os.remove(token_file)

