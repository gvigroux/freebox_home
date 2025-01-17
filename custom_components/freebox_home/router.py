"""Represent the Freebox router and its devices and sensors."""
from datetime import datetime, timedelta
import logging
import os
import asyncio
import json
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


    async def update_all(self, now: Optional[datetime] = None) -> None:
        """Update all nodes"""
        try:
            fbx_nodes: Dict[str, Any] = await self._api.home.get_home_nodes()


        except InsufficientPermissionsError as error:
            _LOGGER.error("InsufficientPermissionsError: You need to browse http://mafreebox.freebox.fr/#Fbx.os.app.settings.Accounts and grant the access policy: \"Gestion de l'alarme et maison connectée\"")
            return

        for fbx_node in fbx_nodes:
            if( fbx_node["category"] not in ["pir","camera","alarm","dws","kfb","basic_shutter","shutter","opener"] ):
                _LOGGER.warning("Node not supported: \n" +str(fbx_node))
                continue
            self.nodes[fbx_node["id"]] = fbx_node

        #fbx_node = json.loads('{"adapter":0,"area":29,"category":"shutter","group":{"label":"Chambre"},"id":25,"label":"Volet Chambre","name":"node_25","props":{"Address":5187680,"ArcId":9},"show_endpoints":[{"category":"","ep_type":"slot","id":0,"label":"Consigne d\'ouverture","name":"position_set","ui":{"access":"w","display":"slider","icon_url":"/resources/images/home/pictos/volet_3.png","range":[0,100],"unit":"%"},"value":0,"value_type":"int","visibility":"normal"},{"category":"","ep_type":"slot","id":1,"label":"Stop","name":"stop","ui":{"access":"w","display":"button"},"value":null,"value_type":"void","visibility":"normal"},{"category":"","ep_type":"slot","id":2,"label":"Toggle","name":"toggle","ui":{"access":"w","display":"button"},"value":null,"value_type":"void","visibility":"normal"},{"category":"","ep_type":"signal","id":4,"label":"Consigne d\'ouverture","name":"position_set","refresh":2000,"ui":{"access":"r","display":"slider","icon_url":"/resources/images/home/pictos/volet_3.png","range":[0,100],"unit":"%"},"value":0,"value_type":"int","visibility":"normal"},{"category":"","ep_type":"signal","id":5,"label":"État","name":"state","refresh":2000,"ui":{"access":"r","display":"text"},"value":"xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx","value_type":"string","visibility":"normal"}],"signal_links":[],"slot_links":[],"status":"active","type":{"abstract":false,"endpoints":[{"ep_type":"slot","id":0,"label":"Consigne d\'ouverture","name":"position_set","value_type":"int","visiblity":"normal"},{"ep_type":"slot","id":1,"label":"Stop","name":"stop","value_type":"void","visiblity":"normal"},{"ep_type":"slot","id":2,"label":"Toggle","name":"toggle","value_type":"void","visiblity":"normal"},{"ep_type":"slot","id":3,"label":"Consigne d\'ouverture","name":"position","value_type":"int","visiblity":"normal"},{"ep_type":"signal","id":4,"label":"Consigne d\'ouverture","name":"position_set","param_type":"void","value_type":"int","visiblity":"normal"},{"ep_type":"signal","id":5,"label":"État","name":"state","param_type":"void","value_type":"string","visiblity":"normal"}],"generic":false,"icon":"/resources/images/home/pictos/volet_3.png","inherit":"node::ios","label":"Volet roulant","name":"node::ios::2","params":{},"physical":true}}')
        #self.nodes[fbx_node["id"]] = fbx_node

    async def close(self) -> None:
        """Close the connection."""
        if self._api is not None:
            await self._api.close()
            self._unsub_dispatcher()
        self._api = None




async def async_get_path(hass, name):
    freebox_path = Store(hass, STORAGE_VERSION, STORAGE_KEY).path
    if not os.path.exists(freebox_path):
        await hass.async_add_executor_job(os.makedirs, freebox_path)
    return Path(f"{freebox_path}/{slugify(name)}.conf")

def get_path(hass, name):
    freebox_path = Store(hass, STORAGE_VERSION, STORAGE_KEY).path
    return Path(f"{freebox_path}/{slugify(name)}.conf")


async def get_api(hass, host: str, port, retry = 0):
    """Get the Freebox API."""

    path = await async_get_path(hass, host)
    api = Freepybox(APP_DESC, path, api_version="latest")
    
    try:
        await api.open(host, port) 
        #loop = asyncio.get_running_loop()
        #await loop.run_in_executor(None, async_func_wrapper, api, host, port)
        
        #loop = asyncio.new_event_loop()
        #fetches = [api.open(host, port)]
        #results = await asyncio.gather(*fetches)
        #res = await asyncio.create_task(api.open(host, port))
        #result = await hass.async_add_executor_job(async_func_wrapper, api, host, port)
        
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

