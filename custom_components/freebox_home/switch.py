import logging
from dataclasses import dataclass
from typing import Any
import os

from .const import DOMAIN
from .base_class import FreeboxBaseClass

from homeassistant.util import slugify
from homeassistant.core import callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.switch import SwitchEntityDescription, SwitchEntity

from .router import (get_path)

_LOGGER = logging.getLogger(__name__)




async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:

    router = hass.data[DOMAIN][entry.unique_id]

    entities = []
    for nodeId, node in router.nodes.items():
        #if node["category"]=="basic_shutter":
        #    entities.append(FreeboxShutterInvertSwitchEntity(hass, router, node))
        if node["category"]=="shutter":
            entities.append(FreeboxShutterInvertSwitchEntity(hass, router, node))
        elif node["category"]=="opener":
            entities.append(FreeboxShutterInvertSwitchEntity(hass, router, node))
        
    async_add_entities(entities, True)




class FreeboxShutterInvertSwitchEntity(FreeboxBaseClass, SwitchEntity):
    _attr_has_entity_name = True

    def __init__(self, hass, router, node):
        super().__init__(hass, router, node)

        self._unique_id = f"{self._router.mac}-node_{self._id}" + '_InvertSwitch'
        self._attr_icon = "mdi:directions-fork"
        self._name = "Inverser commandes"

        self._state = False
        self._path  = get_path(hass, self._unique_id + '_InvertSwitch')
        
        try:
            value = self._path.read_text()
            if( value == "1"):
                self._state = True
        except OSError as e:
            return


    @property
    def translation_key(self):
        return "invert_switch"

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        return self._state

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._path.write_text('1')
        self._state = True

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._path.write_text('0')
        self._state = False

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return True

    @callback
    def _handle_coordinator_update(self, update: bool = True) -> None:
        self._attr_is_on = self.is_on
        if update:
            self.async_write_ha_state()
