from services.mqtt.messages.mqtt_sensor_message import MqttSensorMessage
from services.mqtt.models.mqtt_dio_model import MqttDioModel


class MqttDioMessage(MqttSensorMessage):
    model = MqttDioModel

    def prepare_message(self):
        self.model = MqttDioModel.model_validate_json(self.original_message)

    def sensor_value(self):
        return str(self.model.level)

    def make_identifier(self):
        return str(self.model.index)
