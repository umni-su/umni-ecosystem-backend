#  Copyright (C) 2025 Mikhail Sazanov
#  #
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#  #
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#  #
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

from sqlmodel import select
from database.session import write_session
from entities.device import DeviceEntity
from models.device_model_relations import DeviceModelWithRelations


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
                model: DeviceEntity | None = session.exec(
                    select(DeviceEntity).where(DeviceEntity.name == self.device)
                ).first()
                if isinstance(model, DeviceEntity):
                    self.device_model = DeviceModelWithRelations.model_validate(model.model_dump())
                else:
                    self.device_model = None
