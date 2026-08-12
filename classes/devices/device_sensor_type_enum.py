#  Copyright (C) 2025 Mikhail Sazanov
#  #
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#  #
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#  #
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

from enum import Enum, unique

from classes.l10n.l10n import _


@unique
class DeviceSensorTypeEnum(Enum):
    SWITCH = (100, "Switch", "switch", True, "mdi-toggle-switch-variant")
    INPUT = (101, "Input", "input", False, "mdi-radiobox-indeterminate-variant")
    NUMBER = (102, "Number", "number", False, "mdi-numeric")
    FLOAT = (103, "Number", "float", False, "mdi-numeric")
    BOOLEAN = (104, "Boolean", "boolean", False, "mdi-numeric")
    SETPOINT = (200, "Setpoint", "setpoint", True, "mdi-tune-variant")
    TEMPERATURE = (201, "Temperature", "temperature", False, "mdi-thermometer")
    HUMIDITY = (202, "Humidity", "humidity", False, "mdi-water-percent")
    PRESSURE = (203, "Pressure", "pressure", False, "mdi-gauge")
    BATTERY = (204, "Battery", "battery", False, "mdi-battery")
    ENERGY = (205, "Energy", "energy", False, "mdi-lightning-bolt")
    POWER = (206, "Power", "power", False, "mdi-flash-outline")
    VOLTAGE = (207, "Voltage", "voltage", False, "mdi-sine-wave")
    CURRENT = (208, "Current", "current", False, "mdi-current-ac")
    CO2 = (209, "CO2", "co2", False, "mdi-molecule-co2")
    ILLUMINANCE = (210, "Illuminance", "illuminance", False, "mdi-white-balance-sunny")
    MOTION = (211, "Motion", "motion", False, "mdi-motion-sensor")
    CONTACT = (212, "Contact", "contact", False, "mdi-door-closed-lock")
    ALARM = (213, "Alarm", "alarm", False, "mdi-alert-circle-outline")
    LOCK = (214, "Lock", "lock", True, "mdi-lock")
    FAN = (215, "Fan", "fan", True, "mdi-fan")
    AI = (216, "AI", "ai", False, "mdi-sine-wave")
    NTC = (217, "NTC", "ntc", False, "mdi-thermometer")
    LIGHT = (300, "Light", "light", True, "mdi-lightbulb")
    RGB = (301, "Light RGB", "rgb", True, "mdi-lightbulb")
    RGBA = (302, "Light RGBA", "rgba", True, "mdi-lightbulb")
    COLOR_TEMP = (303, "Color Temp", "color_temp", True, "mdi-lightbulb-outline")
    BRIGHTNESS = (304, "Brightness", "brightness", True, "mdi-brightness-7")
    COLOR_HEX = (305, "Color", "color_hex", True, "mdi-palette")
    STRING = (900, "String", "string", True, "mdi-text")

    def __new__(cls, value, label, ui_component, writable, icon):
        obj = object.__new__(cls)
        obj._value_ = value
        obj._label = label
        obj.ui_component = ui_component
        obj.writable = writable
        obj._icon = icon
        return obj

    @property
    def icon(self):
        """Вернуть иконку"""
        return self._icon

    @property
    def label(self):
        """Вернуть название"""
        return _(self._label)

    @classmethod
    def get_ui_schema(cls):
        return [
            {
                "value": e.value,
                "name": e.name,
                "label": e.label,
                "ui_component": e.ui_component,
                "writable": e.writable,
                "icon": e.icon
            }
            for e in cls
        ]
