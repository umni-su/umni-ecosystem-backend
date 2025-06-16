from services.mqtt.messages.mqtt_sensor_message import MqttSensorMessage
from services.mqtt.models.mqtt_ntc_model import MqttNtcModel


class MqttNtcMessage(MqttSensorMessage):
    model: MqttNtcModel

    def prepare_message(self):
        self.model = MqttNtcModel.model_validate_json(self.original_message)

    def sensor_value(self):
        return str(self.model.temp)

    def make_identifier(self):
        return str(self.model.channel)
