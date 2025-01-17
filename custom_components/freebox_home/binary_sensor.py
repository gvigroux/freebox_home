"""Support for motion detector, door opener detector and check for sensor plastic cover """
import logging

from typing import Dict, Optional
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
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
        #elif node["category"]=="basic_shutter":
        #    entities.append(FreeboxCoverInverter(hass, router, node))
        #elif node["category"]=="shutter":
        #    entities.append(FreeboxCoverInverter(hass, router, node))
        #elif node["category"]=="opener":
        #    entities.append(FreeboxCoverInverter(hass, router, node))
        

        cover_node = next(filter(lambda x: (x["name"]=="cover" and x["ep_type"]=="signal"), node["show_endpoints"]), None)
        if( cover_node != None and cover_node.get("value", None) != None):
            entities.append(FreeboxSensorCover(hass, router, node))

    async_add_entities(entities, True)




''' Freebox motion detector sensor '''
class FreeboxPir(FreeboxBaseClass, BinarySensorEntity):

    def __init__(self, hass, router: FreeboxRouter, node: Dict[str, any]) -> None:
        """Initialize a Pir"""
        super().__init__(hass, router, node)
        self._command_trigger = self.get_command_id(node['type']['endpoints'], "signal", "trigger")
        self._detection = False
        self._unsub_watcher = async_track_time_interval(self._hass, self.async_update_pir, timedelta(seconds=1))

    async def async_update_pir(self, now: Optional[datetime] = None) -> None:
        detection = await self.get_home_endpoint_value(self._command_trigger)
        if( self._detection == detection ):
            self._detection = not detection
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
        return BinarySensorDeviceClass.MOTION
    
    async def async_will_remove_from_hass(self):
        """When entity will be removed from hass."""
        self._unsub_watcher()
        await super().async_will_remove_from_hass()


''' Freebox door opener sensor '''
class FreeboxDws(FreeboxPir):
    def __init__(self, hass, router: FreeboxRouter, node: Dict[str, any]) -> None:
        super().__init__(hass, router, node)

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return BinarySensorDeviceClass.DOOR

'''
class FreeboxDws(FreeboxBaseClass, BinarySensorEntity):
    def __init__(self, hass, router: FreeboxRouter, node: Dict[str, any]) -> None:
        """Initialize a Dws"""
        super().__init__(hass, router, node)
        self._command_trigger = self.get_command_id(node['type']['endpoints'], "signal", "trigger")

        self._detection = False
        self._unsub_watcher = async_track_time_interval(self._hass, self.async_update_pir, timedelta(seconds=1))

    async def async_update_pir(self, now: Optional[datetime] = None) -> None:
        detection = await self.get_home_endpoint_value(self._command_trigger)
        if( self._detection == detection ):
            self._detection = not detection
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
'''

''' Freebox cover check for some sensors (motion detector, door opener detector...) '''
class FreeboxSensorCover(FreeboxBaseClass, BinarySensorEntity):
    def __init__(self, hass, router: FreeboxRouter, node: Dict[str, any]) -> None:
        """Initialize a Cover for anothe Device"""
        # Get cover node
        cover_node = next(filter(lambda x: (x["name"]=="cover" and x["ep_type"]=="signal"), node['type']['endpoints']), None)
        super().__init__(hass, router, node, cover_node)
        self._command_cover = self.get_command_id(node['show_endpoints'], "signal", "cover")
        self._open = False
        self._unsub_watcher = async_track_time_interval(self._hass, self.async_update_pir, timedelta(seconds=3))

    async def async_update_pir(self, now: Optional[datetime] = None) -> None:
        self._open = await self.get_home_endpoint_value(self._command_cover)
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
        return BinarySensorDeviceClass.SAFETY
    
    async def async_will_remove_from_hass(self):
        """When entity will be removed from hass."""
        self._unsub_watcher()
        await super().async_will_remove_from_hass()