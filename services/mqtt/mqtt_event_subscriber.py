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
from models.sensor_model import SensorModelWithDevice
from services.mqtt.payload.mqtt_payload_models import MqttSensorPayloadModel, MqttManageRelayPayloadModel
from services.mqtt.topics.mqtt_topic_enum import MqttTopicEnum


class MqttEventSubscriber:
    def __init__(self, client: mqtt.Client):
        self.client = client
        event_bus.subscribe(EventType.CHANGE_STATE, self.subscribe_change_state)

    def manage_topic(self, sensor: SensorModelWithDevice, topic: MqttTopicEnum):
        return f'{MqttTopicEnum.MANAGE}/{sensor.device.name}/{topic.value}'

    def subscribe_change_state(
            self,
            payload: MqttSensorPayloadModel,
            sensor: SensorModelWithDevice
    ):
        print(f'[{sensor.device.name}->{sensor.identifier}] Fired change state vie MQTT {payload.id},{payload.value}')
        print(f'\tSend data to {self.manage_topic(sensor, MqttTopicEnum.REL)} {sensor.options['index']}')
        self.client.publish(self.manage_topic(sensor, MqttTopicEnum.REL), MqttManageRelayPayloadModel(
            index=sensor.options['index'],
            level=payload.value
        ).model_dump_json())
