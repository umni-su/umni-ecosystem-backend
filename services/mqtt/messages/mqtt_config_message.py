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
from datetime import datetime
from enum import StrEnum
from typing import Union, Dict, Any

from pydantic import Field, BaseModel

from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from database.session import write_session
from models.sensors.config.sensor_adc_config import SensorAdcConfig
from models.sensors.config.sensor_dio_config import SensorInputsConfig, SensorOutputsConfig
from models.sensors.config.sensor_ntc_config import SensorNtcConfig
from models.sensors.config.sensor_onewire_config import SensorOneWireConfig
from models.sensors.config.sensor_opentherm_config import OpenthermConfig
from models.sensors.config.sensor_rf433_config import SensorRf433Config
from models.sensors.opentherm_config_parser import OpenthermConfigParser
from services.mqtt.messages.base_message import BaseMessage
from classes.devices.device_sensor_type_enum import DeviceSensorTypeEnum


class MqttConfigMessageKey(StrEnum):
    ONEWIRE = 'onewire'
    RF433 = 'rf433'
    NTC = 'ntc'
    ADC = 'adc'
    DIO = 'dio'


class MqttConfigMessageModel(BaseModel):
    key: str = Field(...)
    config: Union[
        SensorOneWireConfig |
        SensorRf433Config |
        SensorAdcConfig |
        SensorNtcConfig |
        SensorOutputsConfig |
        SensorInputsConfig |
        OpenthermConfig |
        Dict[str, Any]
        ] = Field(...)


class MqttConfigMessage(BaseMessage):

    def prepare_message(self):
        try:
            self.model: MqttConfigMessageModel = MqttConfigMessageModel.model_validate_json(self.original_message)
            with (write_session() as session):
                if isinstance(self.model.config, SensorOneWireConfig):
                    for _sensor in self.model.config.sensors:
                        try:
                            sensor = self.get_or_new_sensor(
                                device_id=self.topic.device_model.id,
                                identifier=_sensor.sn,
                                capability=self.model.key,
                            )
                            sensor.active = _sensor.active
                            sensor.identifier = _sensor.sn
                            sensor.capability = self.model.key
                            sensor.device_id = self.topic.device_model.id
                            sensor.name = _sensor.label
                            sensor.type = DeviceSensorTypeEnum.TEMPERATURE.value
                            sensor.last_sync = datetime.now()
                            sensor.icon = DeviceSensorTypeEnum.TEMPERATURE.icon
                            session.add(sensor)
                        except Exception as e:
                            Logger.err(f'MqttCnfOwMessage->save() {str(e)}', LoggerType.DEVICES)
                    Logger.info(f'📟⚙️ [{self.topic.original_topic}] onewire config saved successfully',
                                LoggerType.DEVICES)

                elif isinstance(self.model.config, SensorNtcConfig) \
                        or isinstance(self.model.config, SensorAdcConfig):
                    for _sensor in self.model.config.channels:
                        try:
                            identifier = f"{self.model.key}{(_sensor.id + 1)}"
                            sensor = self.get_or_new_sensor(
                                device_id=self.topic.device_model.id,
                                capability=self.model.key,
                                identifier=identifier
                            )
                            sensor.active = _sensor.active
                            sensor.capability = self.model.key
                            sensor.identifier = identifier
                            sensor.device_id = self.topic.device_model.id
                            sensor.name = _sensor.label
                            sensor.type = DeviceSensorTypeEnum.TEMPERATURE.value \
                                if self.model.key == "ntc" \
                                else DeviceSensorTypeEnum.NUMBER.value
                            sensor.icon = DeviceSensorTypeEnum.TEMPERATURE.icon \
                                if self.model.key == "ntc" \
                                else DeviceSensorTypeEnum.NUMBER.icon
                            sensor.last_sync = datetime.now()
                            session.add(sensor)
                        except Exception as e:
                            Logger.err(f'MqttCnfOwMessage->save() {str(e)}', LoggerType.DEVICES)
                    Logger.info(f'📟⚙️ [{self.topic.original_topic}] {self.model.key} config saved successfully',
                                LoggerType.DEVICES)

                elif isinstance(self.model.config, SensorInputsConfig):
                    for _input in self.model.config.inputs:
                        identifier = f"inp{_input.port}"
                        sensor = self.get_or_new_sensor(
                            device_id=self.topic.device_model.id,
                            capability=self.model.key,
                            identifier=identifier
                        )
                        sensor.type = DeviceSensorTypeEnum.INPUT.value
                        sensor.icon = DeviceSensorTypeEnum.INPUT.icon
                        sensor.active = _input.active
                        sensor.capability = self.model.key
                        sensor.identifier = identifier
                        sensor.device_id = self.topic.device_model.id
                        sensor.name = _input.label
                        sensor.last_sync = datetime.now()
                        sensor.options = _input.model_dump()
                        session.add(sensor)
                elif isinstance(self.model.config, SensorOutputsConfig):
                    for _output in self.model.config.outputs:
                        identifier = f"out{_output.index}"
                        sensor = self.get_or_new_sensor(
                            device_id=self.topic.device_model.id,
                            capability=self.model.key,
                            identifier=identifier
                        )
                        sensor.type = DeviceSensorTypeEnum.SWITCH.value
                        sensor.icon = DeviceSensorTypeEnum.SWITCH.icon
                        sensor.active = _output.active
                        sensor.capability = self.model.key
                        sensor.identifier = identifier
                        sensor.device_id = self.topic.device_model.id
                        sensor.name = _output.label
                        sensor.last_sync = datetime.now()
                        sensor.options = _output.model_dump()
                        session.add(sensor)

                elif isinstance(self.model.config, OpenthermConfig):
                    # Основные сенсоры состояния
                    ot_parser = OpenthermConfigParser(
                        config=self.model.config,
                        device_id=self.topic.device_model.id,
                    )
                    ot_parser.save_sensors()
                    Logger.info(f'📟⚙️ [{self.topic.original_topic}] {self.model.key} config saved successfully',
                                LoggerType.DEVICES)

        except Exception as e:
            self.model = None
            Logger.err(str(e), LoggerType.DEVICES)
