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

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship

from entities.device import DeviceEntity
from entities.mixins.created_updated import TimeStampMixin
from entities.mixins.id_column import IdColumnMixin

if TYPE_CHECKING:
    from entities.sensor_history import SensorHistory


class SensorBase:
    device_id: int | None = Field(
        index=True,
        default=None,
        foreign_key="devices.id"
    )
    type: Optional[int] = Field(
        index=True,
        nullable=True,
        description=" -> MqttSensorTypeEnum"
    )
    identifier: str = Field(
        unique=True,
        index=True
    )
    name: str = Field(
        nullable=True
    )
    visible_name: str = Field(
        nullable=True
    )
    options: Optional[dict] = Field(
        sa_column=Column(
            JSON, nullable=True
        )
    )
    value: str | None = Field(
        nullable=True
    )
    photo: str = Field(
        nullable=True
    )
    last_sync: datetime = Field(
        index=True,
        nullable=True
    )


class SensorEntity(
    TimeStampMixin,
    SensorBase,
    IdColumnMixin,
    table=True
):
    __tablename__ = 'device_sensors'

    device: DeviceEntity | None = Relationship(
        back_populates="sensors"
    )
    history: list["SensorHistory"] = Relationship(
        back_populates="sensor"
    )
