"""Support for detectors covers."""
import logging

from typing import Dict, Optional
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import Entity
from .const import DOMAIN, VALUE_NOT_SET
from .router import FreeboxRouter

_LOGGER = logging.getLogger(__name__)

class FreeboxBaseClass(Entity):
    def __init__(self, hass, router: FreeboxRouter, node: Dict[str, any], sub_node = None) -> None:
        _LOGGER.debug(node)
        self._hass = hass
        self._router = router
        self._id    = node["id"]
        self._name  = node["label"].strip()
        self._device_name = node["label"].strip()
        self._unique_id = f"{self._router.mac}-node_{self._id}"
        self._is_device = True

        if(sub_node != None):
            self._name = sub_node["label"].strip()
            self._unique_id += "-" + sub_node["name"].strip()
            #self._is_device = False

        self._available = True
        self._firmware  = node['props'].get('FwVersion', None)
        self._manufacturer = "Free SAS"
        self._model     = ""
        if( node["category"]=="pir" ):
            self._model     = "F-HAPIR01A"
        elif( node["category"]=="camera" ):
            self._model     = "F-HACAM01A"
        elif( node["category"]=="dws" ):
            self._model     = "F-HADWS01A"
        elif( node["category"]=="kfb" ):
            self._model     = "F-HAKFB01A"
            self._is_device = True
        elif( node["category"]=="alarm" ):
            self._model     = "F-MSEC07A"
        elif( node["type"].get("inherit", None)=="node::rts"):
            self._manufacturer  = "Somfy"
            self._model         = "RTS"
        elif( node["type"].get("inherit", None)=="node::ios"):
            self._manufacturer  = "Somfy"
            self._model         = "IOcontrol"

    @property
    def unique_id(self) -> str:
        return self._unique_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def available(self):
        """Return True if entity is available."""
        return self._available

    @property
    def device_info(self):
        """Return the device info."""
        if (self._is_device == False):
            return None
        return {
            "identifiers": {(DOMAIN, self._id)},
            "name": self._device_name,
            "manufacturer": self._manufacturer,
            "model": self._model,
            "sw_version": self._firmware,
        }

    async def set_home_endpoint_value(self, command_id, value):
        if( command_id == VALUE_NOT_SET ):
            _LOGGER.error("Unable to SET a value through the API. Command is VALUE_NOT_SET")
            return False
        await self._router._api.home.set_home_endpoint_value(self._id, command_id, value)
        return True

    async def get_home_endpoint_value(self, command_id):
        if( command_id == VALUE_NOT_SET ):
            _LOGGER.error("Unable to GET a value through the API. Command is VALUE_NOT_SET")
            return VALUE_NOT_SET
        node = await self._router._api.home.get_home_endpoint_value(self._id, command_id)
        return node.get("value", VALUE_NOT_SET)
        
    def get_command_id(self, nodes, ep_type, name ):
        node = next(filter(lambda x: (x["name"]==name and x["ep_type"]==ep_type), nodes), None)
        if( node == None):
            _LOGGER.warning("The Freebox Home device has no value for: " + ep_type + "/" + name)
            return VALUE_NOT_SET
        return node["id"]

    def get_node_value(self, nodes, ep_type, name ):
        node = next(filter(lambda x: (x["name"]==name and x["ep_type"]==ep_type), nodes), None)
        if( node == None):
            _LOGGER.warning("The Freebox Home device has no value for: " + ep_type + "/" + name)
            return VALUE_NOT_SET
        return node.get("value", VALUE_NOT_SET)