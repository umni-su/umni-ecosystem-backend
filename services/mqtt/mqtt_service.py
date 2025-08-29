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

import paho.mqtt.client as mqtt
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from config.dependencies import get_crypto
from entities.configuration import ConfigurationKeys
from responses.mqtt import MqttBody
from services.base_service import BaseService
from services.mqtt.messages.base_message import BaseMessage
from services.mqtt.messages.mqtt_ai_message import MqttAiMessage
from services.mqtt.messages.mqtt_cnf_ai_message import MqttCnfAiMessage
from services.mqtt.messages.mqtt_cnf_dio_message import MqttCnfDioMessage
from services.mqtt.messages.mqtt_cnf_ow_message import MqttCnfOwMessage
from services.mqtt.messages.mqtt_cnf_rf_message import MqttCnfRfMessage
from services.mqtt.messages.mqtt_dio_message import MqttDioMessage
from services.mqtt.messages.mqtt_ntc_message import MqttNtcMessage
from services.mqtt.messages.mqtt_ow_message import MqttOwMessage
from services.mqtt.messages.mqtt_rf_message import MqttRfMessage
from services.mqtt.messages.mqtt_register_message import MqttRegisterMessage
from services.mqtt.topics.mqtt_topic import MqttTopic
from services.mqtt.topics.mqtt_topic_enum import MqttTopicEnum


class MqttService(BaseService):
    name = 'mqtt'
    mqttc: mqtt.Client = None
    model: MqttBody

    def run(self):
        host = self.config.get_setting(ConfigurationKeys.MQTT_HOST).value
        port = int(self.config.get_setting(ConfigurationKeys.MQTT_PORT).value)
        username = self.config.get_setting(ConfigurationKeys.MQTT_USER).value
        password = self.config.get_setting(ConfigurationKeys.MQTT_PASSWORD).value
        self.mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

        self.model = MqttBody(
            host=host,
            port=port,
            user=username,
            password=password
        )

        self.create_connection(self.model)
        self.mqttc.loop_forever()

    # The callback for when the client receives a CONNACK response from the server.
    def on_connect(self, client: mqtt.Client, userdata, flags, reason_code, properties):
        Logger.debug(f"Connected with result code {reason_code}", LoggerType.DEVICES)
        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        client.subscribe("#")

    # The callback for when a PUBLISH message is received from the server.
    def on_message(self, client: mqtt.Client, userdata, msg):
        t = MqttTopic(msg.topic)
        if t.topic == MqttTopicEnum.REGISTER:
            message: MqttRegisterMessage = MqttRegisterMessage(msg.topic, msg.payload)
        elif t.topic == MqttTopicEnum.CNF_DIO:
            message: MqttCnfDioMessage = MqttCnfDioMessage(msg.topic, msg.payload)
        elif t.topic == MqttTopicEnum.CNF_OW:
            message: MqttCnfOwMessage = MqttCnfOwMessage(msg.topic, msg.payload)
        elif t.topic == MqttTopicEnum.CNF_RF433:
            message: MqttCnfRfMessage = MqttCnfRfMessage(msg.topic, msg.payload)
        elif t.topic == MqttTopicEnum.CNF_AI:
            message: MqttCnfAiMessage = MqttCnfAiMessage(msg.topic, msg.payload)
        elif t.topic == MqttTopicEnum.NTC:
            message: MqttNtcMessage = MqttNtcMessage(msg.topic, msg.payload)
        elif t.topic == MqttTopicEnum.AI:
            message: MqttAiMessage = MqttAiMessage(msg.topic, msg.payload)
        elif t.topic == MqttTopicEnum.OW:
            message: MqttOwMessage = MqttOwMessage(msg.topic, msg.payload)
        elif t.topic == MqttTopicEnum.INP:
            message: MqttDioMessage = MqttDioMessage(msg.topic, msg.payload)
        elif t.topic == MqttTopicEnum.REL:
            message: MqttDioMessage = MqttDioMessage(msg.topic, msg.payload)
        elif t.topic == MqttTopicEnum.RF433:
            message: MqttRfMessage = MqttRfMessage(msg.topic, msg.payload)
        else:
            # message: MqttSensorMessage = MqttSensorMessage(msg.topic, msg.payload)
            Logger.debug(msg.topic + " " + str(msg.payload), LoggerType.DEVICES)

            message: BaseMessage = BaseMessage(msg.topic, msg.payload)

        message.save()

    def create_connection(self, model: MqttBody):
        if model.host is not None and model.port is not None:
            self.mqttc.on_connect = self.on_connect
            self.mqttc.on_message = self.on_message
            if model.user is not None and model.password is not None:
                crypto = get_crypto()
                pwd = crypto.decrypt(str(model.password))
                self.mqttc.username_pw_set(
                    username=model.user,
                    password=pwd
                )
            Logger.info(f'Run MQTT with: {model.host}:{model.port}', LoggerType.DEVICES)

            self.mqttc.connect(
                model.host,
                model.port,
                60
            )

            return self.mqttc.is_connected()

        return False

    @staticmethod
    def check_connection(
            model: MqttBody
    ):
        mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

        if model.user is not None and model.password is not None:
            mqttc.username_pw_set(
                username=model.user,
                password=str(model.password)
            )
        mqttc.connect(
            model.host,
            model.port,
            60
        )
        mqttc.loop_start()
        mqttc.loop_stop()
        return mqttc
