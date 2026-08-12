#  Copyright (C) 2026 Mikhail Sazanov
#  #
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""Составные виджеты устройств.

Виджет — вычисляемая "вью-модель" поверх сенсоров устройства (аналог
auto-discovery в Home Assistant):

  * каждый сенсор имеет семантическую роль (power, brightness, color,
    color_temp, mode, setpoint, ...) — берётся из колонки role, а если она
    пуста, выводится из типа сенсора (DeviceSensorTypeEnum);
  * тип виджета (light_rgbcw, switch, thermostat, ...) выводится из набора
    ролей (или задаётся плагином при синхронизации в devices.widget_type);
  * дескриптор виджета собирается из живых сенсоров на каждый запрос —
    ничего не хранится, поэтому он никогда не устаревает.

Никакого состояния в БД сервис не держит — это чистые функции.
"""

import json
from typing import Any, Dict, List, Optional

from classes.devices.device_sensor_type_enum import DeviceSensorTypeEnum
from models.sensor_model import SensorModel, SensorModelWithDevice
from models.widget_model import WidgetControl, WidgetDescriptor

# Роль сенсора по типу (DeviceSensorTypeEnum.value -> роль).
# Дублируется с миграцией 2e9c7f41a8b5 намеренно.
TYPE_ROLE: Dict[int, str] = {
    100: "power",  # SWITCH
    200: "setpoint",  # SETPOINT
    201: "temperature",  # TEMPERATURE
    202: "humidity",  # HUMIDITY
    203: "pressure",  # PRESSURE
    204: "battery",  # BATTERY
    205: "energy",  # ENERGY
    206: "power_meter",  # POWER (измерение, не управление)
    207: "voltage",  # VOLTAGE
    208: "current",  # CURRENT
    209: "co2",  # CO2
    210: "illuminance",  # ILLUMINANCE
    211: "motion",  # MOTION
    212: "contact",  # CONTACT
    213: "alarm",  # ALARM
    214: "lock",  # LOCK
    215: "fan",  # FAN
    217: "temperature",  # NTC (температурный датчик)
    300: "power",  # LIGHT
    301: "color",  # RGB
    302: "color",  # RGBA
    303: "color_temp",  # COLOR_TEMP
    304: "brightness",  # BRIGHTNESS
    305: "color",  # COLOR_HEX
}

# STRING (900) / INPUT (101) с перечислением значений - это режим
MODE_TYPES = {101, 900}

# Бинарные роли-переключатели
BOOL_ROLES = {"power", "lock"}

# Числовые роли
NUMERIC_ROLES = {
    "brightness", "color_temp", "setpoint", "temperature", "humidity", "fan",
}

# Порядок controls внутри светового виджета
LIGHT_ORDER = ("power", "brightness", "mode", "color", "color_temp")

# Порядок controls для остальных типов
CONTROL_ORDER = {
    "switch": ("power",),
    "fan": ("power", "fan"),
    "lock": ("lock",),
    "thermostat": ("setpoint", "temperature", "humidity"),
}


def _attr(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _type_value(sensor: Any) -> Optional[int]:
    stype = _attr(sensor, "type")
    if isinstance(stype, DeviceSensorTypeEnum):
        return stype.value
    if isinstance(stype, int):
        return stype
    return None


def _type_writable(sensor: Any) -> bool:
    stype = _attr(sensor, "type")
    if isinstance(stype, DeviceSensorTypeEnum):
        return bool(stype.writable)
    return False


def _options(sensor: Any) -> Dict[str, Any]:
    options = _attr(sensor, "options")
    if isinstance(options, dict):
        return options
    return {}


def _parse_enum_values(values: Any) -> Optional[List[str]]:
    """Парсинг перечисления значений (для роли mode).

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


def _parse_range(values: Any) -> tuple[Optional[float], Optional[float]]:
    """Парсинг диапазона {min, max} из options (для color_temp)."""
    if isinstance(values, str):
        try:
            values = json.loads(values)
        except (TypeError, ValueError):
            return None, None
    if not isinstance(values, dict):
        return None, None
    try:
        return float(values["min"]), float(values["max"])
    except (TypeError, KeyError, ValueError):
        return None, None


def derive_role(
        sensor_type: Any,
        options: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Роль сенсора, выводимая из типа и опций (без учёта колонки role)."""
    options = options or {}
    if isinstance(sensor_type, DeviceSensorTypeEnum):
        val = sensor_type.value
    else:
        val = sensor_type
    role = TYPE_ROLE.get(val)
    if role is None and val in MODE_TYPES:
        if _parse_enum_values(options.get("values")):
            role = "mode"
    return role


def sensor_role(sensor: SensorModelWithDevice) -> Optional[str]:
    """Роль сенсора: из колонки role, иначе выводится из типа."""
    explicit = _attr(sensor, "role")
    if explicit:
        return str(explicit)
    return derive_role(_attr(sensor, "type"), _options(sensor))


def _sensors_by_role(sensors: List[SensorModelWithDevice]) -> Dict[str, List[Any]]:
    grouped: Dict[str, List[SensorModelWithDevice]] = {}
    for sensor in sensors or []:
        role = sensor_role(sensor)
        if role:
            grouped.setdefault(role, []).append(sensor)
    return grouped


def infer_widget_name(sensors: List[SensorModelWithDevice]) -> Optional[str]:
    """Тип виджета по набору ролей сенсоров (аналог auto-discovery)."""
    grouped = _sensors_by_role(sensors)

    def has(role: str) -> bool:
        return role in grouped

    if has("setpoint") and has("temperature"):
        return "thermostat"
    # Свет: power + хотя бы один из компаньонов
    if has("power") and (
            has("brightness") or has("color") or has("color_temp") or has("mode")):
        if has("color") and has("color_temp") and has("mode"):
            return "light_rgbcw"
        if has("color"):
            return "light_rgb"
        if has("color_temp"):
            return "light_cct"
        return "light"
    if has("fan"):
        return "fan"
    if has("lock"):
        return "lock"
    if has("power"):
        return "switch"
    return None


def _to_bool(raw: Any) -> bool:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return raw != 0
    if isinstance(raw, str):
        return raw.strip().lower() in ("1", "true", "yes", "on")
    return bool(raw)


def _to_number(raw: Any) -> Any:
    if isinstance(raw, bool):
        return float(raw)
    try:
        f = float(str(raw).strip())
        return int(f) if f.is_integer() else f
    except (TypeError, ValueError):
        return raw


def _widget_value(sensor: Any, role: str) -> Any:
    """Приводит значение сенсора (в БД это строка) к типу по роли."""
    raw = _attr(sensor, "value")
    if raw is None:
        return None
    if role in BOOL_ROLES:
        return _to_bool(raw)
    if role in NUMERIC_ROLES:
        return _to_number(raw)
    return raw


def _control_sensor(sensor: Any, role: str) -> WidgetControl:
    options = _options(sensor)
    writable = options.get("writable")
    if writable is None:
        writable = _type_writable(sensor)

    control = WidgetControl(
        role=role,
        sensor_id=_attr(sensor, "id"),
        sensor_type=_type_value(sensor),
        capability=_attr(sensor, "capability"),
        identifier=_attr(sensor, "identifier"),
        name=_attr(sensor, "visible_name") or _attr(sensor, "name")
             or _attr(sensor, "capability"),
        unit=_attr(sensor, "unit"),
        writable=bool(writable),
        readonly=not bool(writable),
        value=_widget_value(sensor, role),
        options=options or None,
    )

    if role == "brightness":
        control.min, control.max = 0.0, 100.0
    elif role == "color_temp":
        lo, hi = _parse_range(options.get("values"))
        if lo is None:
            lo, hi = _parse_range(options.get("range"))
        control.min, control.max = lo, hi
    elif role == "mode":
        control.values = _parse_enum_values(options.get("values"))

    return control


def _build_controls(
        sensors: List[Any],
        roles_order: tuple,
        allowed_roles: Optional[set] = None,
) -> List[WidgetControl]:
    grouped = _sensors_by_role(sensors)
    controls: List[WidgetControl] = []
    for role in roles_order:
        if role not in grouped:
            continue
        for sensor in grouped[role]:
            if allowed_roles is None or role in allowed_roles:
                controls.append(_control_sensor(sensor, role))
    return controls


def build_widget(
        widget_type: Optional[str],
        widget_name: Optional[str],
        device_name: Optional[str],
        sensors: List[SensorModelWithDevice],
) -> Optional[WidgetDescriptor]:
    """Собирает дескриптор виджета из живых сенсоров.

    Тип берётся из widget_type (задаётся плагином/юзером), если пуст —
    выводится из ролей. Возвращает None, если составного виджета нет
    (чистый датчик - фронт рисует обычный список сенсоров).
    """
    sensors = [s for s in sensors if s.active]
    wtype = widget_type or infer_widget_name(sensors)
    if not wtype:
        return None

    if wtype.startswith("light"):
        controls = _build_controls(sensors, LIGHT_ORDER)
    else:
        controls = _build_controls(sensors, CONTROL_ORDER.get(wtype, ()))

    if not controls:
        return None

    return WidgetDescriptor(
        type=wtype,
        name=widget_name or device_name,
        controls=controls,
    )
