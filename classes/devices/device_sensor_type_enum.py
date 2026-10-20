#  Copyright (C) 2025 Mikhail Sazanov
#  #
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  #
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

import json
from enum import Enum, unique
from typing import Any, Dict, List, Optional

from classes.l10n.l10n import _


@unique
class DeviceSensorTypeEnum(Enum):
    """Тип сенсора устройства.

    Единый источник правды по семантике типа:
      * writable — поддерживает ли сенсор запись (единственный источник
        для SensorModel.writable; options["writable"] больше не эталон);
      * default_role — семантическая роль по умолчанию (power, color,
        temperature, ...); None у generic-типов (INPUT, NUMBER, FLOAT,
        BOOLEAN, AI, STRING), роль которых задаётся явно или выводится
        из options.values (mode).
    """
    SWITCH = (100, "Switch", "switch", True, "mdi-toggle-switch-variant", "power")
    INPUT = (101, "Input", "input", False, "mdi-radiobox-indeterminate-variant", None)
    NUMBER = (102, "Number", "number", False, "mdi-numeric", None)
    FLOAT = (103, "Number", "float", False, "mdi-numeric", None)
    BOOLEAN = (104, "Boolean", "boolean", False, "mdi-numeric", None)
    SETPOINT = (200, "Setpoint", "setpoint", True, "mdi-tune-variant", "setpoint")
    TEMPERATURE = (201, "Temperature", "temperature", False, "mdi-thermometer", "temperature")
    HUMIDITY = (202, "Humidity", "humidity", False, "mdi-water-percent", "humidity")
    PRESSURE = (203, "Pressure", "pressure", False, "mdi-gauge", "pressure")
    BATTERY = (204, "Battery", "battery", False, "mdi-battery", "battery")
    ENERGY = (205, "Energy", "energy", False, "mdi-lightning-bolt", "energy")
    POWER = (206, "Power", "power", False, "mdi-flash-outline", "power_meter")
    VOLTAGE = (207, "Voltage", "voltage", False, "mdi-sine-wave", "voltage")
    CURRENT = (208, "Current", "current", False, "mdi-current-ac", "current")
    CO2 = (209, "CO2", "co2", False, "mdi-molecule-co2", "co2")
    ILLUMINANCE = (210, "Illuminance", "illuminance", False, "mdi-white-balance-sunny", "illuminance")
    MOTION = (211, "Motion", "motion", False, "mdi-motion-sensor", "motion")
    CONTACT = (212, "Contact", "contact", False, "mdi-door-closed-lock", "contact")
    ALARM = (213, "Alarm", "alarm", False, "mdi-alert-circle-outline", "alarm")
    LOCK = (214, "Lock", "lock", True, "mdi-lock", "lock")
    FAN = (215, "Fan", "fan", True, "mdi-fan", "fan")
    AI = (216, "AI", "ai", False, "mdi-sine-wave", None)
    NTC = (217, "NTC", "ntc", False, "mdi-thermometer", "temperature")
    LIGHT = (300, "Light", "light", True, "mdi-lightbulb", "power")
    RGB = (301, "Light RGB", "rgb", True, "mdi-lightbulb", "color")
    RGBA = (302, "Light RGBA", "rgba", True, "mdi-lightbulb", "color")
    COLOR_TEMP = (303, "Color Temp", "color_temp", True, "mdi-lightbulb-outline", "color_temp")
    BRIGHTNESS = (304, "Brightness", "brightness", True, "mdi-brightness-7", "brightness")
    COLOR_HEX = (305, "Color", "color_hex", True, "mdi-palette", "color")
    STRING = (900, "String", "string", True, "mdi-text", None)

    def __new__(cls, value, label, ui_component, writable, icon, default_role):
        obj = object.__new__(cls)
        obj._value_ = value
        obj._label = label
        obj.ui_component = ui_component
        obj.writable = writable
        obj._icon = icon
        obj._default_role = default_role
        return obj

    @property
    def icon(self):
        """Вернуть иконку"""
        return self._icon

    @property
    def label(self):
        """Вернуть название"""
        return _(self._label)

    @property
    def default_role(self) -> Optional[str]:
        """Семантическая роль по умолчанию (None у generic-типов)."""
        return self._default_role

    @classmethod
    def parse_enum_values(cls, values: Any) -> Optional[List[str]]:
        """Парсинг перечисления значений из options сенсора.

        Облако Tuya отдаёт values для Enum-типа строкой, которая может быть
        JSON-массивом ('["white","colour","scene"]') или списком без кавычек
        ('[white,colour,scene]'); для Integer это dict {min, max, scale, ...}.
        """
        if values is None:
            return None
        if isinstance(values, list):
            return [str(v) for v in values] or None
        if isinstance(values, dict):
            keys = [str(k) for k in values.keys()]
            return keys or None
        if isinstance(values, str):
            s = values.strip()
            try:
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    return [str(v) for v in parsed] or None
                if isinstance(parsed, dict):
                    return [str(k) for k in parsed.keys()] or None
            except (TypeError, ValueError):
                pass
            s = s.strip().strip('[]')
            if not s:
                return None
            parts = [p.strip().strip('"\'').strip() for p in s.split(',')]
            parts = [p for p in parts if p]
            return parts or None
        return None

    @classmethod
    def derive_role(
            cls,
            sensor_type: Any,
            options: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Роль сенсора, выводимая из типа и опций (без учёта колонки role).

        INPUT (101) / STRING (900) с перечислением значений — это режим.
        """
        options = options or {}
        if isinstance(sensor_type, cls):
            val = sensor_type.value
        else:
            val = sensor_type
        try:
            stype = cls(val)
        except ValueError:
            return None
        if stype.default_role:
            return stype.default_role
        if stype in (cls.INPUT, cls.STRING) and cls.parse_enum_values(options.get("values")):
            return "mode"
        return None

    @classmethod
    def get_ui_schema(cls):
        return [
            {
                "value": e.value,
                "name": e.name,
                "label": e.label,
                "ui_component": e.ui_component,
                "writable": e.writable,
                "icon": e.icon,
                "default_role": e.default_role
            }
            for e in cls
        ]
