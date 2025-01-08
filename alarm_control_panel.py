"""Support for Freebox alarm"""
import logging
import json
import time
import async_timeout

from typing import Dict, Optional
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.components.alarm_control_panel import AlarmControlPanelEntity
from datetime import datetime, timedelta
from .base_class import FreeboxBaseClass

from .const import DOMAIN, VALUE_NOT_SET
from .router import FreeboxRouter


from homeassistant.components.alarm_control_panel.const import (
    AlarmControlPanelEntityFeature.ARM_AWAY,
    AlarmControlPanelEntityFeature.ARM_CUSTOM_BYPASS,
    AlarmControlPanelEntityFeature.ARM_HOME,
    AlarmControlPanelEntityFeature.ARM_NIGHT,
    AlarmControlPanelEntityFeature.TRIGGER,
)

from homeassistant.const import (
    STATE_ALARM_DISARMED,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_NIGHT,
    STATE_ALARM_ARMED_CUSTOM_BYPASS,
    STATE_ALARM_PENDING,
    STATE_ALARM_ARMING,
    STATE_ALARM_DISARMING,
    STATE_ALARM_TRIGGERED,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities):
    router = hass.data[DOMAIN][entry.unique_id]
    entities = []

    for nodeId, node in router.nodes.items():
        if node["category"]=="alarm":
            entities.append(FreeboxAlarm(hass, router, node))

    async_add_entities(entities, True)


class FreeboxAlarm(FreeboxBaseClass, AlarmControlPanelEntity):

    def __init__(self, hass, router: FreeboxRouter, node: Dict[str, any]) -> None:
        """Initialize an Alarm"""
        super().__init__(hass, router, node)

        self._command_trigger   = VALUE_NOT_SET # Trigger
        self._command_alarm1    = VALUE_NOT_SET # Alarme principale
        self._command_alarm2    = VALUE_NOT_SET # Alarme secondaire
        self._command_skip      = VALUE_NOT_SET # Passer le délai
        self._command_off       = VALUE_NOT_SET # Désactiver l'alarme
        self._command_pin       = VALUE_NOT_SET # Code PIN
        self._command_sound     = VALUE_NOT_SET # Puissance des bips
        self._command_volume    = VALUE_NOT_SET # Puissance de la sirène
        self._command_timeout1  = VALUE_NOT_SET # Délai avant armement
        self._command_timeout2  = VALUE_NOT_SET # Délai avant sirène
        self._command_timeout3  = VALUE_NOT_SET # Durée de la sirène

        for endpoint in filter(lambda x:(x["ep_type"] == "slot"), node['type']['endpoints']):
            if( endpoint["name"] == "pin" ):
                self._command_pin = endpoint["id"]
            elif( endpoint["name"] == "sound" ):
                self._command_sound = endpoint["id"]
            elif( endpoint["name"] == "volume" ):
                self._command_volume = endpoint["id"]
            elif( endpoint["name"] == "timeout1" ):
                self._command_timeout1 = endpoint["id"]
            elif( endpoint["name"] == "timeout2" ):
                self._command_timeout2 = endpoint["id"]
            elif( endpoint["name"] == "timeout3" ):
                self._command_timeout3 = endpoint["id"]
            elif( endpoint["name"] == "trigger" ):
                self._command_trigger = endpoint["id"]
            elif( endpoint["name"] == "alarm1" ):
                self._command_alarm1 = endpoint["id"]
            elif( endpoint["name"] == "alarm2" ):
                self._command_alarm2 = endpoint["id"]
            elif( endpoint["name"] == "skip" ):
                self._command_skip = endpoint["id"]
            elif( endpoint["name"] == "off" ):
                self._command_off = endpoint["id"]

        self._command_state = self.get_command_id(node['type']['endpoints'], "signal", "state" )

        self.set_state("idle")
        self._unsub_watcher = None
        self._supported_features = SUPPORT_ALARM_ARM_AWAY
        self.update_parameters(node)

    @property
    def state(self) -> str:
        return self._state

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        return self._supported_features

    async def async_alarm_disarm(self, code=None) -> None:
        """Send disarm command."""
        if( await self.set_home_endpoint_value(self._command_off, {"value": None})):
            time.sleep(1)
            self.schedule_update_ha_state(True)

    async def async_alarm_arm_away(self, code=None) -> None:
        """Send arm away command."""
        if( await self.set_home_endpoint_value(self._command_alarm1, {"value": None})):
            time.sleep(1)
            self._unsub_watcher = async_track_time_interval(self.hass, self.sync_update_during_arming, timedelta(seconds=1))

    async def async_alarm_arm_home(self, code=None) -> None:
        await self.async_alarm_arm_night(code)

    async def async_alarm_arm_night(self, code=None) -> None:
        """Send arm night command."""
        if( await self.set_home_endpoint_value(self._command_alarm2, {"value": None})):
            time.sleep(1)
            self._unsub_watcher = async_track_time_interval(self.hass, self.sync_update_during_arming, timedelta(seconds=1))


    async def sync_update_during_arming(self, now: Optional[datetime] = None) -> None:
        self.set_state(await self.get_home_endpoint_value( self._command_state))
        self.async_write_ha_state()

    async def async_update(self):
        """Get the state & name and update it."""
        state = await self.get_home_endpoint_value( self._command_state)
        if( state == "idle" and self._unsub_watcher != None):
            self._unsub_watcher()
        self.update_parameters(self._router.nodes[self._id])


    def update_parameters(self, node):

        #search Alarm2
        has_alarm2 = False
        for nodeId, local_node in self._router.nodes.items():
            alarm2 = next(filter(lambda x: (x["name"]=="alarm2" and x["ep_type"]=="signal"), local_node['show_endpoints']), None)
            if( alarm2 != None and alarm2["value"] == True):
                has_alarm2 = True
                break

        if( has_alarm2 ):
            self._supported_features = SUPPORT_ALARM_ARM_AWAY | SUPPORT_ALARM_ARM_NIGHT
        else:
            self._supported_features = SUPPORT_ALARM_ARM_AWAY


        self._name = node["label"].strip()
        
        # Parse all endpoints values
        for endpoint in filter(lambda x:(x["ep_type"] == "signal"), node['show_endpoints']):
            if( endpoint["name"] == "pin" ):
                self._pin = endpoint["value"]
            elif( endpoint["name"] == "sound" ):
                self._sound = endpoint["value"]
            elif( endpoint["name"] == "volume" ):
                self._high_volume = endpoint["value"]
            elif( endpoint["name"] == "timeout1" ):
                self._timeout1 = endpoint["value"]
            elif( endpoint["name"] == "timeout3" ):
                self._timeout2 = endpoint["value"]
            elif( endpoint["name"] == "timeout3" ):
                self._timeout3 = endpoint["value"]
            elif( endpoint["name"] == "battery" ):
                self._battery = endpoint["value"]

    def set_state(self, state):
        if( state == "alarm1_arming"):
            self._state = STATE_ALARM_ARMING
        elif( state == "alarm2_arming"):
            self._state = STATE_ALARM_ARMING
        elif( state == "alarm1_armed"):
            self._state = STATE_ALARM_ARMED_AWAY
        elif( state == "alarm2_armed"):
            self._state = STATE_ALARM_ARMED_NIGHT
        elif( state == "alarm1_alert_timer"):
            self._state = STATE_ALARM_TRIGGERED
        elif( state == "alarm2_alert_timer"):
            self._state = STATE_ALARM_TRIGGERED
        elif( state == "alert"):
            self._state = STATE_ALARM_TRIGGERED
        else:
            self._state = STATE_ALARM_DISARMED

