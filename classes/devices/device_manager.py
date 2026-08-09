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

from attr.validators import is_callable

from classes.devices.device_registry import device_registry
from classes.devices.device_sensor_type_enum import DeviceSensorTypeEnum
from classes.devices.device_source_enum import DeviceSource, DeviceFeature
from models.device_model_relations import DeviceModelWithRelations
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from config.dependencies import get_ecosystem
from database.session import write_session
from models.device_model import DeviceModel, DeviceModelMain
from models.sensor_model import SensorModel, SensorModelWithDevice
from models.sensors.config.sensor_opentherm_config import BoundItem
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

    def get_device(self, device_id: int) -> Optional[DeviceModelWithRelations]:
        """Получить устройство"""
        return DeviceRepository.get_device(device_id)

    def get_sensor(self, sensor_id: int) -> Optional[SensorModelWithDevice]:
        """Получить сенсор"""
        return SensorRepository.get_sensor(sensor_id)

    def get_device_sensors(self, device_id: int) -> List[SensorModel]:
        """Получить все сенсоры устройства"""
        with write_session() as session:
            return session.query(SensorModel).filter_by(device_id=device_id).all()

    def sensor_is_opentherm(self, sensor: SensorModelWithDevice):
        return sensor.capability == "opentherm"

    def sensor_get_bounds(self, sensor: SensorModelWithDevice) -> Optional[BoundItem]:
        try:
            return BoundItem.model_validate(sensor.options)
        except Exception as e:
            Logger.err(str(e), LoggerType.DEVICES)
            return None

    def sensor_is_output(self, sensor: SensorModelWithDevice):
        return sensor.capability == "outputs" and self.sensor_is_relay(sensor)

    def sensor_is_opencollector(self, sensor: SensorModelWithDevice):
        return sensor.capability == "opencollectors" and self.sensor_is_relay(sensor)

    def sensor_is_relay(self, sensor: SensorModelWithDevice):
        return sensor.type == DeviceSensorTypeEnum.SWITCH

    def sensor_is_input(self, sensor: SensorModelWithDevice):
        return sensor.type == DeviceSensorTypeEnum.INPUT

    def sensor_is_ai(self, sensor: SensorModelWithDevice):
        return sensor.type == DeviceSensorTypeEnum.AI

    def sensor_is_ntc(self, sensor: SensorModelWithDevice):
        return sensor.type == DeviceSensorTypeEnum.NTC

    def sensor_is_setpoint(self, sensor: SensorModelWithDevice):
        return sensor.type == DeviceSensorTypeEnum.SETPOINT

    # ========== COMMANDS (PLUGIN DELEGATED) ==========

    def _get_plugin_for_device(self, device_id: int):
        """Получить плагин, который управляет устройством"""
        device = self.get_device(device_id)
        if not device:
            raise ValueError(f"Device {device_id} not found")

        plugin: "BasePlugin" = self.plugins.get_plugin_by_name(device.plugin.name)
        if not plugin:
            raise ValueError(f"Plugin for source '{device.type}' not running")

        return plugin, device

    def set_value(
            self,
            device_name: str,
            sensor_identifier: str,
            value: Any) -> bool:
        """
        Установить значение сенсора (включить, изменить яркость и т.д.)
        Делегирует плагину.
        """

        device_model = DeviceRepository.get_device_by_name(
            name=device_name
        )
        if device_model is None:
            return False

        sensor = SensorRepository.get_sensor_by_device_and_identifier(
            device_id=device_model.id,
            identifier=sensor_identifier
        )

        if sensor is None:
            return False

        device = sensor.device

        if isinstance(device, DeviceModelMain):
            plugin, device = self._get_plugin_for_device(sensor.device_id)

            # Вызываем метод плагина
            success = plugin.set_sensor_value(
                sensor=sensor,
                value=value
            )
            return success

        return False

    def update_value_in_db(self, device_name: str,
                           sensor_identifier: str,
                           value: Any) -> bool:
        """
        Обновление значения сенсора в базе данных
        """
        device_model = DeviceRepository.get_device_by_name(
            name=device_name
        )
        if device_model is None:
            return False

        sensor = SensorRepository.get_sensor_by_device_and_identifier(
            device_id=device_model.id,
            identifier=sensor_identifier
        )

        if sensor is None:
            return False
        return self.registry.update_sensor_value(sensor.id, value)

    def locate_device(self, device_id: int) -> bool:
        plugin, device = self._get_plugin_for_device(device_id)

        if callable(plugin.locate) and device.external_id is not None:
            return plugin.locate(device.external_id)
        return False


device_manager = DeviceManager()
