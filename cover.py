"""Support for Freebox covers."""
import logging
import json
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.components.cover import CoverEntity, DEVICE_CLASS_SHUTTER
from .const import DOMAIN
from .base_class import FreeboxBaseClass

from homeassistant.const import (
    STATE_CLOSED,
    STATE_CLOSING,
    STATE_OPEN,
    STATE_OPENING,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    router = hass.data[DOMAIN][entry.unique_id]
    entities = []

    for nodeId, node in router.nodes.items():
        if node["category"]=="basic_shutter":
            entities.append(FreeboxBasicShutter(hass, router, node))
        elif node["category"]=="shutter":
            entities.append(FreeboxShutter(hass, router, node))

    async_add_entities(entities, True)


class FreeboxBasicShutter(FreeboxBaseClass,CoverEntity):

    def __init__(self, hass, router, node) -> None:
        """Initialize a Cover"""
        super().__init__(hass, router, node)
        self._command_up    = self.get_command_id(node['show_endpoints'], "slot", "up")
        self._command_stop  = self.get_command_id(node['show_endpoints'], "slot", "stop")
        self._command_down  = self.get_command_id(node['show_endpoints'], "slot", "down")
        self._command_state = self.get_command_id(node['show_endpoints'], "signal", "state")
        self._state         = self.get_node_value(node['show_endpoints'], "signal", "state")

    @property
    def device_class(self) -> str:
        return DEVICE_CLASS_SHUTTER

    @property
    def current_cover_position(self):
        return None

    @property
    def current_cover_tilt_position(self):
        return None

    @property
    def is_closed(self):
        """Return if the cover is closed or not."""
        if(self._state == STATE_OPEN):
            return False
        if(self._state == STATE_CLOSED):
            return True
        return None

    async def async_open_cover(self, **kwargs):
        """Open cover."""
        await self.set_home_endpoint_value(self._command_up, {"value": None})
        self._state = STATE_OPEN

    async def async_close_cover(self, **kwargs):
        """Close cover."""
        await self.set_home_endpoint_value(self._command_down, {"value": None})
        self._state = STATE_CLOSED

    async def async_stop_cover(self, **kwargs):
        """Stop cover."""
        await self.set_home_endpoint_value(self._command_stop, {"value": None})
        self._state = None

    async def async_update(self):
        """Get the state & name and update it."""
        node = self._router.nodes[self._id];
        self._name = node["label"].strip()
        self._state = self.convert_state(await self.get_home_endpoint_value(self._command_state))
        

    def convert_state(self, state):
        if( state ): 
            return STATE_CLOSED
        elif( state is not None):
            return STATE_OPEN
        else:
            return None

class FreeboxShutter(FreeboxBaseClass,CoverEntity):

    def __init__(self, hass, router, node) -> None:
        """Initialize a Cover"""
        super().__init__(hass, router, node)
        self._command_position = self.get_command_id(node['type']['endpoints'], "slot", "position_set")
        self._command_up = self.get_command_id(node['type']['endpoints'], "slot", "position_set")
        self._command_down = self.get_command_id(node['type']['endpoints'], "slot", "position_set")
        self._command_stop  = self.get_command_id(node['show_endpoints'], "slot", "stop")
        self._command_toggle = self.get_command_id(node['show_endpoints'], "slot", "toggle")
        self._command_state = self.get_command_id(node['type']['endpoints'], "signal", "position_set")
        self._state         = self.get_node_value(node['show_endpoints'], "signal", "state")

    @property
    def device_class(self) -> str:
        return DEVICE_CLASS_SHUTTER

    @property
    def current_cover_position(self):
        return self._state

    @property
    def current_cover_tilt_position(self):
        return None

    @property
    def is_closed(self):
        """Return if the cover is closed or not."""
        if(self._state == 100):
            return True
        return False

    async def async_set_cover_position(self, position, **kwargs):
        """Set cover position."""
        await self.set_home_endpoint_value(self._command_position, {"value": position})
        self._state = STATE_OPEN

    async def async_open_cover(self, **kwargs):
        """Open cover."""
        await self.set_home_endpoint_value(self._command_up, {"value": 0})

    async def async_close_cover(self, **kwargs):
        """Close cover."""
        await self.set_home_endpoint_value(self._command_down, {"value": 100})

    async def async_stop_cover(self, **kwargs):
        """Stop cover."""
        await self.set_home_endpoint_value(self._command_stop, {"value": None})
        self._state = None

    async def async_update(self):
        """Get the state & name and update it."""
        node = self._router.nodes[self._id];
        self._name = node["label"].strip()
        self._state = await self.get_home_endpoint_value(self._command_state)      
