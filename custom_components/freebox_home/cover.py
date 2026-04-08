"""Support for Freebox covers."""
import logging
from homeassistant.components.cover import CoverEntity, CoverDeviceClass
from .const import DOMAIN, DUMMY, VALUE_NOT_SET
from .base_class import FreeboxBaseClass
from homeassistant.helpers.entity_registry import async_get

from homeassistant.const import (
    STATE_CLOSED,
    STATE_OPEN,
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
        elif node["category"]=="opener":
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
        return CoverDeviceClass.SHUTTER

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
        self._command_stop = self.get_command_id(node['show_endpoints'], "slot", "stop")
        self._command_toggle = self.get_command_id(node['show_endpoints'], "slot", "toggle")
        self._command_state = self.get_command_id(node['type']['endpoints'], "signal", "position_set")
        self._current_state = self.get_node_value(node['show_endpoints'], "signal", "state")

        # Go over all entities to find the switch
        self._invert_entity_id = None
        entity_registry = async_get(hass)
        for entity in entity_registry.entities.values():
            if (entity.unique_id == self.unique_id + "_InvertSwitch"):
                self._invert_entity_id = entity.entity_id


    def get_invert_status(self):
        if(self._invert_entity_id == None):
            return False
        state = self._hass.states.get(self._invert_entity_id)
        if( state == None ):
            return False
        if( state.state == "on" ):
            return True
        return False

    def get_corrected_state(self, value):
        if( value == None ):
            return value
        if( self.get_invert_status() ):
            if( DUMMY ):
                _LOGGER.error("Value converted from " + str(value) + " to " + str(100 - value))
            return 100 - value
        if( DUMMY ):
            _LOGGER.error("Value " + str(value))
        return value
    

    @property
    def device_class(self) -> str:
        if("garage" in self._name.lower()):
            return CoverDeviceClass.GARAGE
        return CoverDeviceClass.SHUTTER

    @property
    def current_cover_position(self):
        return self._current_state

    @property
    def current_cover_tilt_position(self):
        return None

    @property
    def is_closed(self):
        """Return if the cover is closed or not."""
        if(self._current_state == 0):
            return True
        return False

    async def async_set_cover_position(self, **kwargs):
        """Set cover position."""
        position = kwargs.get("position")
        await self.set_home_endpoint_value(self._command_position, {"value": self.get_corrected_state(position)})
        self._current_state = position

    async def async_open_cover(self, **kwargs):
        """Open cover."""
        if( self.get_invert_status() == False ):
            await self.set_home_endpoint_value(self._command_up, {"value": 0})
        else:
            await self.set_home_endpoint_value(self._command_down, {"value": 100})
        self._current_state = 100

    async def async_close_cover(self, **kwargs):
        """Close cover."""
        if( self.get_invert_status() == True ):
            await self.set_home_endpoint_value(self._command_up, {"value": 0})
        else:
            await self.set_home_endpoint_value(self._command_down, {"value": 100})
        self._current_state = 0

    async def async_stop_cover(self, **kwargs):
        """Stop cover."""
        await self.set_home_endpoint_value(self._command_stop, {"value": None})
        self._current_state = 50

    async def async_update(self):
        """Get the state & name and update it."""
        if( self._id >= 1000 ) and (DUMMY): 
            _LOGGER.error("Current state: " + str(self._current_state) + " Freebox: " + str(self.get_corrected_state(self._current_state)))
        else:
            self._current_state = self.get_corrected_state(await self.get_home_endpoint_value(self._command_state))
