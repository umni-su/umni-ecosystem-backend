from datetime import datetime
from typing import Optional

from entities.camera import CameraEntity
from entities.camera_area import CameraAreaEntity
from entities.camera_recording import CameraRecordingEntity
from entities.mixins.created_updated import TimeStampMixin
from entities.mixins.id_column import IdColumnMixin
from sqlmodel import Field, Relationship


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
