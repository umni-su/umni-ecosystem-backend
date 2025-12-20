# Copyright (C) 2025 Mikhail Sazanov
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

import paho.mqtt.client as mqtt

from classes.events.event_bus import event_bus
from classes.events.event_types import EventType
from models.enums.device_model_source import DeviceModelSource
from models.sensor_model import SensorModelWithDevice
from services.mqtt.payload.mqtt_payload_models import MqttSensorPayloadModel, MqttManageRelayPayloadModel
from services.mqtt.topics.mqtt_sensor_type_enum import MqttSensorTypeEnum
from services.mqtt.topics.mqtt_topic_enum import MqttTopicEnum


class MqttEventSubscriber:
    def __init__(self, client: mqtt.Client):
        self.client = client

        event_bus.subscribe(EventType.SENSOR_SET_STATE, self.run_set_sensor_state)

    def run_set_sensor_state(
            self,
            sensor: SensorModelWithDevice,
            payload: MqttSensorPayloadModel | MqttManageRelayPayloadModel
    ):
        topic = None
        real_payload = payload
        if sensor.device.source == DeviceModelSource.SERVICE_MQTT.value:
            if sensor.type == MqttSensorTypeEnum.RELAY:
                real_payload = MqttManageRelayPayloadModel(
                    index=sensor.options.get('index'),
                    level=payload.value
                )
                topic = MqttTopicEnum.REL

        if topic is not None:
            self.client.publish(
                topic=f'{MqttTopicEnum.MANAGE}/{sensor.device.name}/{topic}',
                payload=real_payload.model_dump_json())
