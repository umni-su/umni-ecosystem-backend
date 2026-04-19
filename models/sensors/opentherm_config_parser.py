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
from typing import Optional

from sqlmodel import select, Session

from classes.devices.device_sensor_type_enum import DeviceSensorTypeEnum
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from database.session import write_session
from entities.sensor_entity import SensorEntity
from models.sensors.config.sensor_opentherm_config import OpenthermConfig, BoundItem
from models.sensors.sensor_utils import get_or_new_sensor


class OpenthermConfigParser:
    config: OpenthermConfig
    device_id: int
    key: str = 'opentherm'

    def __init__(self, config: OpenthermConfig, device_id: int):
        self.config = config
        self.device_id = device_id

    def get_or_new_sensor(
            self,
            device_id: int,
            identifier: str,
            capability: str | None
    ) -> SensorEntity:
        return get_or_new_sensor(
            device_id=device_id,
            identifier=identifier,
            capability=capability,
        )

    def save_sensors(self):
        for field_name, field_value in self.config.model_dump().items():
            with write_session() as session:
                try:
                    if isinstance(field_value, dict):
                        pass
                    elif isinstance(field_value, list):
                        pass
                    else:
                        sensor = self.get_or_new_sensor(
                            device_id=self.device_id,
                            capability=self.key,
                            identifier=field_name
                        )
                        sensor.identifier = field_name
                        sensor.device_id = self.device_id
                        sensor.name = field_name.upper()
                        sensor.type = self.get_sensor_type_by_opentherm_key(field_name).value
                        sensor.active = self.config.adapter_success
                        sensor.capability = self.key
                        sensor.value = str(field_value)
                        sensor.icon = self.__map_icon(sensor)
                        if sensor.type == DeviceSensorTypeEnum.SETPOINT.value:
                            sensor.options = self.__get_bounds(sensor)
                        session.add(sensor)
                        session.commit()
                        self.__update_history(
                            sensor=sensor,
                            session=session,
                        )
                except Exception as e:
                    Logger.err(str(e), LoggerType.DEVICES)

    def __map_icon(self, sensor: SensorEntity):
        mappings = {
            DeviceSensorTypeEnum.SWITCH.value: DeviceSensorTypeEnum.SWITCH.icon,
            DeviceSensorTypeEnum.TEMPERATURE.value: DeviceSensorTypeEnum.TEMPERATURE.icon,
            DeviceSensorTypeEnum.NUMBER.value: DeviceSensorTypeEnum.NUMBER.icon,
            DeviceSensorTypeEnum.FLOAT.value: DeviceSensorTypeEnum.FLOAT.icon,
            DeviceSensorTypeEnum.BOOLEAN.value: DeviceSensorTypeEnum.BOOLEAN.icon,
            DeviceSensorTypeEnum.SETPOINT.value: DeviceSensorTypeEnum.SETPOINT.icon,
        }
        return mappings.get(sensor.type)

    def __get_bounds(self, sensor: SensorEntity) -> Optional[BoundItem]:
        mapping = {
            "ch_sp": self.config.bounds.ch.model_dump(),
            "dhw_sp": self.config.bounds.dhw.model_dump(),
            "hcr": self.config.bounds.hcr.model_dump(),
            "mod": BoundItem(
                min=0,
                max=100
            ).model_dump(),
        }
        return mapping.get(sensor.identifier)

    def __update_history(self, sensor: SensorEntity, session: Session) -> bool:
        if not sensor.active:
            return False
        try:
            from entities.sensor_history import SensorHistory
            history = SensorHistory()
            history.sensor_id = sensor.id
            history.value = sensor.value
            session.add(history)
            session.commit()
            return True
        except Exception as e:
            Logger.err(str(e), LoggerType.DEVICES)
        return False

    def get_sensor_type_by_opentherm_key(self, key: str) -> DeviceSensorTypeEnum:
        if key in [
            'en',
            'ch_en',
            'dhw_en',
            'ch2_en',
            'cool_en',
            'otc_en'
        ]:
            return DeviceSensorTypeEnum.SWITCH
        elif key in [
            'ch_sp',
            'dhw_sp',
            'mod'
        ]:
            return DeviceSensorTypeEnum.SETPOINT
        elif key in [
            'boiler_temperature',
            'return_temperature',
            'dhw_temperature',
            'outside_temperature'
        ]:
            return DeviceSensorTypeEnum.TEMPERATURE
        elif key in [
            'ready',
            'adapter_success',
            'ch_active',
            'dhw_active',
            'flame_on',
            'is_fault'
        ]:
            return DeviceSensorTypeEnum.BOOLEAN
        else:
            return DeviceSensorTypeEnum.NUMBER
