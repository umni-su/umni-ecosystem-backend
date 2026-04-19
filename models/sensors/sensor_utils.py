# Copyright (C) 2026 Mikhail Sazanov
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
from sqlmodel import select

from database.session import write_session
from entities.sensor_entity import SensorEntity


def get_or_new_sensor(
        device_id: int,
        identifier: str,
        capability: str | None
) -> SensorEntity:
    with write_session() as session:
        sensor = SensorEntity()
        existing = session.exec(
            select(SensorEntity)
            .where(SensorEntity.device_id == device_id)
            .where(SensorEntity.capability == capability)
            .where(SensorEntity.identifier == identifier)
        ).first()
        if isinstance(existing, SensorEntity):
            sensor = existing
        return sensor
