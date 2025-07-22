from datetime import datetime
from typing import Optional

from entities.camera import CameraEntity
from entities.camera_area import CameraAreaEntity
from entities.camera_recording import CameraRecordingEntity
from entities.enums.camera_record_type_enum import CameraRecordTypeEnum
from entities.mixins.created_updated import TimeStampMixin
from entities.mixins.id_column import IdColumnMixin
from sqlmodel import Field, Relationship

from services.cameras.classes.roi_tracker import ROIEventType


class CameraEventBase:
    camera_id: int = Field(nullable=False, index=True, foreign_key="cameras.id")
    area_id: int | None = Field(nullable=True, index=True, foreign_key="camera_areas.id")
    action: ROIEventType | None = Field(nullable=True)
    type: CameraRecordTypeEnum | None = Field(nullable=True, index=True)
    start: datetime = Field(default_factory=datetime.now, nullable=False)
    end: datetime = Field(nullable=True)
    resized: str = Field(nullable=True)
    original: str = Field(nullable=True)
    duration: int | None = Field(nullable=True)


class CameraEventEntity(TimeStampMixin, CameraEventBase, IdColumnMixin, table=True):
    __tablename__ = 'camera_events'
    camera: CameraEntity | None = Relationship(
        sa_relationship_kwargs=dict(lazy="subquery"),
        back_populates="events")
    area: CameraAreaEntity | None = Relationship(
        sa_relationship_kwargs=dict(lazy="subquery"),
        back_populates="events")

    # Для режима записи видео
    camera_recording_id: Optional[int] = Field(default=None, foreign_key="camera_recordings.id")
    recording: Optional[CameraRecordingEntity] = Relationship(
        sa_relationship_kwargs=dict(lazy="subquery"),
        back_populates="events"
    )
