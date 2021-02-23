"""Support for PIR"""
import logging

from typing import Dict, Optional
from homeassistant.components.binary_sensor import BinarySensorEntity, DEVICE_CLASS_MOTION, DEVICE_CLASS_DOOR, DEVICE_CLASS_SAFETY
from homeassistant.helpers.event import async_track_time_interval
from datetime import datetime, timedelta

from .base_class import FreeboxBaseClass
from .const import DOMAIN, VALUE_NOT_SET
from .router import FreeboxRouter


_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    router = hass.data[DOMAIN][config_entry.unique_id]
    entities = []

    for nodeId, node in router.nodes.items():
        if node["category"]=="pir":
            entities.append(FreeboxPir(hass, router, node))
        elif node["category"]=="dws":
            entities.append(FreeboxDws(hass, router, node))

        cover_node = next(filter(lambda x: (x["name"]=="cover" and x["ep_type"]=="signal"), node["show_endpoints"]), None)
        if( cover_node != None and cover_node.get("value", None) != None):
            entities.append(FreeboxCover(hass, router, node))

    async_add_entities(entities, True)


class FreeboxPir(FreeboxBaseClass, BinarySensorEntity):

    def __init__(self, hass, router: FreeboxRouter, node: Dict[str, any]) -> None:
        """Initialize a Pir"""
        super().__init__(hass, router, node)
        self._command_trigger = self.get_command_id(node['type']['endpoints'], "signal", "trigger")
        self._detection = False
        self._unsub_watcher = async_track_time_interval(self._hass, self.async_update_pir, timedelta(seconds=1))

    async def async_update_pir(self, now: Optional[datetime] = None) -> None:
        state = await self._router._api.home.get_home_endpoint_value(self._id, self._command_trigger)
        if( self._detection == state["value"] ):
            self._detection = not state["value"]
            self.async_write_ha_state()

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self._detection

    @property
    def should_poll(self):
        """Return True if entity has to be polled for state."""
        return False

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return DEVICE_CLASS_MOTION
    
    async def async_will_remove_from_hass(self):
        """When entity will be removed from hass."""
        self._unsub_watcher()
        await super().async_will_remove_from_hass()


class FreeboxDws(FreeboxBaseClass, BinarySensorEntity):
    def __init__(self, hass, router: FreeboxRouter, node: Dict[str, any]) -> None:
        """Initialize a Dws"""
        super().__init__(hass, router, node)
        self._command_trigger = self.get_command_id(node['type']['endpoints'], "signal", "trigger")

        self._detection = False
        self._unsub_watcher = async_track_time_interval(self._hass, self.async_update_pir, timedelta(seconds=1))

    async def async_update_pir(self, now: Optional[datetime] = None) -> None:
        state = await self._router._api.home.get_home_endpoint_value(self._id, self._command_trigger)
        if( self._detection == state["value"] ):
            self._detection = not state["value"]
            self.async_write_ha_state()

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self._detection

    @property
    def should_poll(self):
        """Return True if entity has to be polled for state."""
        return False

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return DEVICE_CLASS_DOOR
    
    async def async_will_remove_from_hass(self):
        """When entity will be removed from hass."""
        self._unsub_watcher()
        await super().async_will_remove_from_hass()

        
class FreeboxCover(FreeboxBaseClass, BinarySensorEntity):
    def __init__(self, hass, router: FreeboxRouter, node: Dict[str, any]) -> None:
        """Initialize a Cover for anothe Device"""
        # Get cover node
        cover_node = next(filter(lambda x: (x["name"]=="cover" and x["ep_type"]=="signal"), node['type']['endpoints']), None)
        super().__init__(hass, router, node, cover_node)
        self._command_cover = self.get_command_id(node['show_endpoints'], "signal", "cover")
        self._open = False
        self._unsub_watcher = async_track_time_interval(self._hass, self.async_update_pir, timedelta(seconds=1))

    async def async_update_pir(self, now: Optional[datetime] = None) -> None:
        state = await self._router._api.home.get_home_endpoint_value(self._id, self._command_cover)
        self._open = state["value"]
        self.async_write_ha_state()

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self._open

    @property
    def should_poll(self):
        """Return True if entity has to be polled for state."""
        return False

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return DEVICE_CLASS_SAFETY
    
    async def async_will_remove_from_hass(self):
        """When entity will be removed from hass."""
        self._unsub_watcher()
        await super().async_will_remove_from_hass()