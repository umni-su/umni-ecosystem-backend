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

from sqlmodel import Field, Relationship

from entities.mixins.created_updated import TimeStampMixin
from entities.mixins.id_column import IdColumnMixin
from entities.sensor import Sensor


class SensorHistoryBase:
    sensor_id: int | None = Field(
        index=True,
        default=None,
        foreign_key="device_sensors.id"
    )
    value: str = Field(
        nullable=True
    )


class SensorHistory(
    TimeStampMixin,
    SensorHistoryBase,
    IdColumnMixin,
    table=True
):
    __tablename__ = 'device_sensors_history'

    sensor: Sensor | None = Relationship(
        back_populates="history"
    )
