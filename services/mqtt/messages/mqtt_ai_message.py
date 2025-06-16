from services.mqtt.messages.mqtt_sensor_message import MqttSensorMessage
from services.mqtt.models.mqtt_ai_model import MqttAiModel


class MqttAiMessage(MqttSensorMessage):
    model: MqttAiModel

    def prepare_message(self):
        self.model = MqttAiModel.model_validate_json(self.original_message)

    def sensor_value(self):
        return str(self.model.value)

    def make_identifier(self):
        return str(self.model.channel)
