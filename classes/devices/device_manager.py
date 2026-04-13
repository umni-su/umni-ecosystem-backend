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

from typing import Optional, Any, List, TYPE_CHECKING, Union

from classes.devices.device_registry import device_registry
from classes.devices.device_sensor_type_enum import DeviceSensorTypeEnum
from classes.devices.device_source_enum import DeviceSource, DeviceFeature
from classes.devices.umni_device_options import UmniDeviceOutputOptions
from classes.devices.umni_http_device_commands import UmniHttpDeviceCommands
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from config.dependencies import get_ecosystem
from database.session import write_session
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

    def get_sensor(self, sensor_id: int) -> Optional[SensorModelWithDevice]:
        """Получить сенсор"""
        return SensorRepository.get_sensor(sensor_id)

    def get_device_sensors(self, device_id: int) -> List[SensorModel]:
        """Получить все сенсоры устройства"""
        with write_session() as session:
            return session.query(SensorModel).filter_by(device_id=device_id).all()

    def sensor_is_relay(self, sensor: SensorModelWithDevice):
        return sensor.type == DeviceSensorTypeEnum.RELAY

    def sensor_is_output(self, sensor: SensorModelWithDevice):
        return self.sensor_is_relay(sensor)

    def sensor_is_input(self, sensor: SensorModelWithDevice):
        return sensor.type == DeviceSensorTypeEnum.INPUT

    def sensor_is_ai(self, sensor: SensorModelWithDevice):
        return sensor.type == DeviceSensorTypeEnum.AI

    def sensor_is_ntc(self, sensor: SensorModelWithDevice):
        return sensor.type == DeviceSensorTypeEnum.NTC

    def set_value_core(self, sensor: SensorModelWithDevice, value: Optional[Union[int | float | str]]):
        if self.sensor_is_output(sensor):
            ip = device_registry.get_device_ip(sensor.device_id)
            try:
                if isinstance(sensor.options, dict):
                    options = UmniDeviceOutputOptions.model_validate(sensor.options)
                    if value is not None:
                        uapi = UmniHttpDeviceCommands(ip)
                        res = uapi.switch_output(
                            index=options.index,
                            level=1 if int(value) == 1 else 0
                        )
                        return res['success'] or False
            except Exception as e:
                Logger.err(str(e), LoggerType.DEVICES)

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
        device = sensor.device
        success = False

        if not sensor:
            raise ValueError(f"Sensor {sensor_id} not found")

        if isinstance(device, DeviceModelMain):
            if self.from_core(device):
                # Device from UMNI core, use UMNI API
                success = self.set_value_core(sensor, value)
            elif self.from_plugin(device):
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

        return False

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
