from services.mqtt.messages.mqtt_sensor_message import MqttSensorMessage
from services.mqtt.models.mqtt_ow_model import MqttOwModel


class MqttOwMessage(MqttSensorMessage):
    model: MqttOwModel

    def prepare_message(self):
        self.model = MqttOwModel.model_validate_json(self.original_message)

    def make_identifier(self):
        return str(self.model.sn)

    def sensor_value(self):
        return str(self.model.temp)
