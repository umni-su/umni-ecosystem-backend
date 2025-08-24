import datetime
import re
from classes.logger import Logger
from database.session import write_session
from services.mqtt.messages.base_message import BaseMessage
from services.mqtt.models.mqtt_cnf_ai_ntc_model import MqttCnfAnalogPortsModel, MqttCnfAnalogPortModel
from services.mqtt.topics.mqtt_sensor_type_enum import MqttSensorTypeEnum


class MqttCnfAiMessage(BaseMessage):
    model: MqttCnfAnalogPortsModel = None

    def prepare_message(self):
        try:
            self.model = MqttCnfAnalogPortsModel.model_validate_json(self.original_message)
        except Exception as e:
            print(e)

    def save(self):
        if self.model is None:
            return
        with write_session() as session:
            for (key, item) in self.model:
                _key = MqttSensorTypeEnum.NTC
                if key == 'ai1' or key == 'ai2':
                    _key = MqttSensorTypeEnum.AI
                try:
                    ai_port: MqttCnfAnalogPortModel = item
                    identifier = '.'.join([
                        'dev',
                        str(self.topic.device_model.id),
                        re.sub(r"(\d+)", "", key),
                        str(ai_port.channel)
                    ])
                    sensor = self.get_or_new_sensor(identifier)
                    sensor.device_id = self.topic.device_model.id
                    sensor.identifier = identifier
                    sensor.type = _key.value
                    sensor.name = ai_port.label
                    sensor.options = ai_port.model_dump()
                    sensor.last_sync = datetime.datetime.now()
                    session.add(sensor)
                except Exception as e:
                    print(e)
            Logger.info(f'📟⚙️ [{self.topic.original_topic}] AI config saved successfully')
            session.commit()
