from sqlmodel import select

from database.database import get_separate_session

from entities.device import Device


class MqttTopic:
    original_topic: str
    prefix: str | None = None
    device: str | None = None
    topic: str | None = None
    device_entity: Device | None = None

    def __init__(self, original_topic):
        self.original_topic = original_topic
        expl = self.original_topic.split('/')
        if len(expl) > 2:
            # This is register topic
            self.prefix = expl[0]
            self.device = expl[1]
            del expl[0:2]
            self.topic = "/".join(expl)
            with get_separate_session() as session:
                self.device_entity = session.exec(
                    select(Device).where(Device.name == self.device)
                ).first()
