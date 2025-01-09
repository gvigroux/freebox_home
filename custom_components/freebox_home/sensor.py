from homeassistant.const import PERCENTAGE
from homeassistant.components.sensor import SensorDeviceClass
from .base_class import FreeboxBaseClass
from .const import DOMAIN

async def async_setup_entry(hass, config_entry, async_add_entities):
    router = hass.data[DOMAIN][config_entry.unique_id]
    entities = []

    for nodeId, node in router.nodes.items():
        battery_node = next(filter(lambda x: (x["name"]=="battery" and x["ep_type"]=="signal"), node["show_endpoints"]), None)
        if( battery_node != None and battery_node.get("value", None) != None):
            entities.append(FreeboxBatterySensor(hass, router, node, battery_node))

    async_add_entities(entities, True)


class FreeboxBatterySensor(FreeboxBaseClass):

    def __init__(self, hass, router, node, sub_node) -> None:
        """Initialize a Pir"""
        super().__init__(hass, router, node, sub_node)

    @property
    def device_class(self):
        """Return the devices' state attributes."""
        return SensorDeviceClass.BATTERY

    @property
    def state(self):
        """Return the current state of the device."""
        return self.get_node_value(self._router.nodes[self._id]["show_endpoints"],"signal","battery")

    @property
    def unit_of_measurement(self):
        """Return the unit_of_measurement of the device."""
        return PERCENTAGE