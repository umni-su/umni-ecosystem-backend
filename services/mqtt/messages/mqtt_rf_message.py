from services.mqtt.messages.mqtt_sensor_message import MqttSensorMessage
from services.mqtt.models.mqtt_rf_item_model import MqttRfItemModel


class MqttRfMessage(MqttSensorMessage):
    model: MqttRfItemModel

    def prepare_message(self):
        self.model = MqttRfItemModel.model_validate_json(self.original_message)

    def sensor_value(self):
        return str(self.model.state)

    def make_identifier(self):
        return str(self.model.serial)
