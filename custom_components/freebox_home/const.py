"""Freebox Home component constants."""
import socket

DOMAIN      = "freebox_home"
API_VERSION = "v8"

PLATFORMS = ["switch", "cover", "camera", "alarm_control_panel", "binary_sensor", "sensor", ]

APP_DESC = {
    "app_id": "hass",
    "app_name": "Home Assistant",
    "app_version": "0.106",
    "device_name": socket.gethostname(),
}

# to store the cookie
STORAGE_KEY = DOMAIN
STORAGE_VERSION = 1

#cover
ATTR_MODEL = "model"

#default Value
VALUE_NOT_SET = -1


