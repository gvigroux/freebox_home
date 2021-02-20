import logging

from typing import Dict, Optional
from homeassistant.const import DEVICE_CLASS_BATTERY, PERCENTAGE

from .base_class import FreeboxBaseClass
from .const import DOMAIN, VALUE_NOT_SET
from .router import FreeboxRouter



async def async_setup_entry(hass, config_entry, async_add_entities):
    router = hass.data[DOMAIN][config_entry.unique_id]
    entities = []

    for nodeId, node in router.nodes.items():
        battery_node = next(filter(lambda x: (x["name"]=="battery" and x["ep_type"]=="signal"), node["show_endpoints"]), None)
        if( battery_node != None and battery_node.get("value", None) != None):
            entities.append(FreeboxSensor(hass, router, node))

    async_add_entities(entities, True)


class FreeboxSensor(FreeboxBaseClass):

    def __init__(self, hass, router: FreeboxRouter, node: Dict[str, any]) -> None:
        """Initialize a Pir"""
        super().__init__(hass, router, node)

    @property
    def device_class(self):
        """Return the devices' state attributes."""
        return DEVICE_CLASS_BATTERY

    @property
    def state(self):
        """Return the current state of the device."""
        return self.get_node_value(self._router.nodes[self._id]["show_endpoints"],"signal","battery")

    @property
    def unit_of_measurement(self):
        """Return the unit_of_measurement of the device."""
        return PERCENTAGE