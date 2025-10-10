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
from typing import Optional

from entities.camera import CameraEntity
from entities.camera_area import CameraAreaEntity
from entities.camera_recording import CameraRecordingEntity
from entities.mixins.created_updated import TimeStampMixin
from entities.mixins.id_column import IdColumnMixin
from sqlmodel import Field, Relationship

from entities.mixins.pagination_mixin import PaginationMixin


class CameraEventBase:
    camera_id: int = Field(
        nullable=False,
        index=True,
        foreign_key="cameras.id"
    )
    area_id: int | None = Field(
        nullable=True,
        index=True,
        foreign_key="camera_areas.id"
    )
    action: Optional[int] | None = Field(
        index=True,
        nullable=True,
        description=" -> ROIEventType"
    )
    type: Optional[int] | None = Field(
        nullable=True,
        index=True,
        description=" -> CameraRecordTypeEnum"
    )
    start: datetime = Field(
        index=True,
        default_factory=datetime.now,
        nullable=False
    )
    end: datetime = Field(
        index=True,
        nullable=True
    )
    resized: str = Field(
        nullable=True
    )
    original: str = Field(
        nullable=True
    )
    duration: int | None = Field(
        index=True,
        nullable=True
    )


class CameraEventEntity(
    TimeStampMixin,
    CameraEventBase,
    IdColumnMixin,
    table=True
):
    __tablename__ = 'camera_events'

    camera: CameraEntity | None = Relationship(
        # sa_relationship_kwargs=dict(lazy="selectin"),
        back_populates="events")
    area: CameraAreaEntity | None = Relationship(
        # sa_relationship_kwargs=dict(lazy="selectin"),
        back_populates="events")

    # Для режима записи видео
    camera_recording_id: Optional[int] = Field(
        index=True,
        default=None,
        foreign_key="camera_recordings.id"
    )
    recording: Optional[CameraRecordingEntity] | None = Relationship(
        # sa_relationship_kwargs=dict(lazy="selectin"),
        back_populates="events"
    )
