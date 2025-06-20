import paho.mqtt.client as mqtt
import classes.ecosystem as eco
from classes.crypto.crypto import Crypto
from classes.logger import Logger
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
from services.mqtt.messages.mqtt_sensor_message import MqttSensorMessage
from services.mqtt.messages.mqtt_register_message import MqttRegisterMessage
from services.mqtt.topics.mqtt_topic import MqttTopic
from services.mqtt.topics.mqtt_topic_enum import MqttTopicEnum


class MqttService(BaseService):
    name = 'mqtt'
    mqttc: mqtt.Client = None
    model: MqttBody

    def __init__(self):
        super().__init__()

    def run(self):
        host = eco.Ecosystem.config.get_setting(ConfigurationKeys.MQTT_HOST).value
        port = eco.Ecosystem.config.get_setting(ConfigurationKeys.MQTT_PORT).value
        username = eco.Ecosystem.config.get_setting(ConfigurationKeys.MQTT_USER).value
        password = eco.Ecosystem.config.get_setting(ConfigurationKeys.MQTT_PASSWORD).value
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
        Logger.debug(f"Connected with result code {reason_code}")
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
            Logger.debug(msg.topic + " " + str(msg.payload))

            message: BaseMessage = BaseMessage(msg.topic, msg.payload)

        message.save()

    def create_connection(self, model: MqttBody):
        if model.host is not None and model.port is not None:
            self.mqttc.on_connect = self.on_connect
            self.mqttc.on_message = self.on_message
            if model.user is not None and model.password is not None:
                pwd = Crypto.decrypt(str(model.password))
                self.mqttc.username_pw_set(
                    username=model.user,
                    password=pwd
                )
            Logger.info(f'Run MQTT with: {model.host}:{model.port}')

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
