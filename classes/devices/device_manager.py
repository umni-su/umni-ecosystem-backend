# Copyright (C) 2026 Mikhail Sazanov
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from typing import Optional, Any, Dict, List, TYPE_CHECKING, Union

from classes.devices.device_registry import device_registry
from classes.devices.device_source_enum import DeviceSource, DeviceFeature
from config.dependencies import get_ecosystem
from database.session import write_session
from entities.sensor_entity import SensorEntity
from models.device_model import DeviceModel, DeviceModelMain
from models.sensor_model import SensorModel, SensorModelWithDevice
from repositories.device_repository import DeviceRepository
from repositories.sensor_repository import SensorRepository

if TYPE_CHECKING:
    from plugins.base_plugin import BasePlugin


class DeviceManager:
    """Управление устройствами. Делегирует команды плагинам."""

    def __init__(self):
        self._plugins = None
        self.registry = device_registry

    @property
    def plugins(self):
        if self._plugins is None:
            ecosystem = get_ecosystem()
            self._plugins = ecosystem.service_runner.get_service_by_name('plugins')
        return self._plugins

    @classmethod
    def from_core(cls, device: DeviceModel | DeviceModelMain) -> bool:
        return device.source == DeviceSource.CORE.value

    @classmethod
    def from_plugin(cls, device: DeviceModel | DeviceModelMain) -> bool:
        return device.source == DeviceSource.PLUGINS.value

    @classmethod
    def from_core_mqtt(cls, device: DeviceModel | DeviceModelMain) -> bool:
        return cls.from_core(device) and device.feature == DeviceFeature.MQTT.value

    @classmethod
    def from_core_http(cls, device: DeviceModel | DeviceModelMain) -> bool:
        return cls.from_core(device) and device.feature == DeviceFeature.HTTP.value

    # ========== GETTERS ==========

    def get_device(self, device_id: int) -> Optional[DeviceModel]:
        """Получить устройство"""
        return DeviceRepository.get_device(device_id)

    def get_sensor(self, sensor_id: int) -> Optional[SensorModel]:
        """Получить сенсор"""
        return SensorRepository.get_sensor(sensor_id)

    def get_device_sensors(self, device_id: int) -> List[SensorModel]:
        """Получить все сенсоры устройства"""
        with write_session() as session:
            return session.query(SensorModel).filter_by(device_id=device_id).all()

    def set_value_core(self, sensor_id: int, value: Optional[Union[int | float | str]]):
        sensor_with_device = SensorRepository.update_sensor_value(sensor_id, value)
        if isinstance(sensor_with_device, SensorModelWithDevice):
            if self.from_core_http(sensor_with_device.device):
                # http command to local umni core device
                pass;
            elif self.from_core_mqtt(sensor_with_device.device):
                # mqtt command to local umni core device
                pass;

    # ========== COMMANDS (PLUGIN DELEGATED) ==========

    def _get_plugin_for_device(self, device_id: int):
        """Получить плагин, который управляет устройством"""
        device = self.get_device(device_id)
        if not device:
            raise ValueError(f"Device {device_id} not found")

        plugin: "BasePlugin" = self.plugins.get_plugin_by_name(device.type)
        if not plugin:
            raise ValueError(f"Plugin for source '{device.type}' not running")

        return plugin, device

    def set_value(self, sensor_id: int, value: Any) -> bool:
        """
        Установить значение сенсора (включить, изменить яркость и т.д.)
        Делегирует плагину.
        """
        sensor = self.get_sensor(sensor_id)
        if not sensor:
            raise ValueError(f"Sensor {sensor_id} not found")

        if sensor.readonly:
            raise ValueError(f"Sensor {sensor_id} is read-only")

        # Проверяем границы
        # if sensor.min_value is not None and value < sensor.min_value:
        #     value = sensor.min_value
        # if sensor.max_value is not None and value > sensor.max_value:
        #     value = sensor.max_value

        # Получаем плагин и делегируем
        plugin, device = self._get_plugin_for_device(sensor.device_id)

        # Вызываем метод плагина
        success = plugin.set_sensor_value(
            external_id=device.external_id,
            capability=sensor.capability,
            identifier=sensor.identifier,
            value=value
        )

        if success:
            # Обновляем локальное значение
            self.registry.update_sensor_value(sensor_id, value)

        return success

    def turn_on(self, sensor_id: int) -> bool:
        """Включить (для switch)"""
        return self.set_value(sensor_id, 1)

    def turn_off(self, sensor_id: int) -> bool:
        """Выключить (для switch)"""
        return self.set_value(sensor_id, 0)

    def toggle(self, sensor_id: int) -> bool:
        """Переключить состояние"""
        sensor = self.get_sensor(sensor_id)
        if not sensor:
            raise ValueError(f"Sensor {sensor_id} not found")

        current = 1 if sensor.value == "1" else 0
        return self.set_value(sensor_id, 1 - current)

    def set_brightness(self, sensor_id: int, brightness: int) -> bool:
        """Установить яркость (0-255)"""
        return self.set_value(sensor_id, brightness)

    def set_color(self, sensor_id: int, r: int, g: int, b: int) -> bool:
        """Установить цвет RGB"""
        return self.set_value(sensor_id, {"r": r, "g": g, "b": b})


device_manager = DeviceManager()
