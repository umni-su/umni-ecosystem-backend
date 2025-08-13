from sqlmodel import select

from database.database import write_session

from entities.device import Device
from models.device_model import DeviceModelWithRelations


class MqttTopic:
    original_topic: str
    prefix: str | None = None
    device: str | None = None
    topic: str | None = None
    device_model: DeviceModelWithRelations | None = None

    def __init__(self, original_topic):
        self.original_topic = original_topic
        expl = self.original_topic.split('/')
        if len(expl) > 2:
            # This is register topic
            self.prefix = expl[0]
            self.device = expl[1]
            del expl[0:2]
            self.topic = "/".join(expl)
            with write_session() as session:
                model: Device | None = session.exec(
                    select(Device).where(Device.name == self.device)
                ).first()
                if isinstance(model, Device):
                    self.device_model = DeviceModelWithRelations.model_validate(model.model_dump())
                else:
                    self.device_model = None
