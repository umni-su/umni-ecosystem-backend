import datetime

from sqlmodel import select

import database.database as db
from entities.device import Device
from entities.sensor import Sensor
from services.mqtt.topics.mqtt_topic import MqttTopic


class BaseMessage:
    date: datetime
    topic: MqttTopic
    original_message: str
    model: object
    identifier: str | None = None
    has_device: bool = False
    unique_prefix: str | None = None

    def __init__(self, topic: str, message: bytes):
        self.date = datetime.datetime.now()
        self.topic = MqttTopic(topic)
        self.original_message = message.decode()
        self.prepare_message()
        self.has_device = self.topic.device_model is not None
        if self.has_device:
            self.unique_prefix = '.'.join(
                [
                    'dev',
                    str(self.topic.device_model.id),
                    self.topic.topic.replace('/', '.')
                ]
            )
            add = self.make_identifier()
            if len(add) > 0:
                self.identifier = '.'.join([
                    self.unique_prefix,
                    self.make_identifier()
                ])

    def prepare_message(self):
        pass

    def save(self):
        pass

    def get_or_new_sensor(self, identifier: str) -> Sensor:
        with db.write_session() as session:
            sensor = Sensor()
            existing = session.exec(
                select(Sensor).where(Sensor.identifier == identifier)
            ).first()
            if isinstance(existing, Sensor):
                sensor = existing
            return sensor

    def make_identifier(self):
        return ''
