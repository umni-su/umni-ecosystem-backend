from datetime import datetime

from entities.camera import CameraEntity
from entities.camera_area import CameraAreaEntity
from entities.enums.camera_record_type_enum import CameraRecordTypeEnum
from entities.mixins.created_updated import TimeStampMixin
from entities.mixins.id_column import IdColumnMixin
from sqlmodel import Field, Relationship

from services.cameras.classes.roi_tracker import ROIEvent, ROIEventType


class CameraEventBase:
    camera_id: int = Field(nullable=False, index=True, foreign_key="cameras.id")
    area_id: int | None = Field(nullable=True, index=True, foreign_key="camera_areas.id")
    action: ROIEventType | None = Field(nullable=True)
    type: CameraRecordTypeEnum | None = Field(nullable=True, index=True)
    start: datetime = Field(default_factory=datetime.now, nullable=False)
    end: datetime = Field(nullable=True)
    screenshot: str = Field(nullable=True)
    file: str = Field(nullable=True)


class CameraEventEntity(TimeStampMixin, CameraEventBase, IdColumnMixin, table=True):
    __tablename__ = 'camera_events'
    camera: CameraEntity | None = Relationship(
        sa_relationship_kwargs=dict(lazy="subquery"),
        back_populates="events")
    area: CameraAreaEntity | None = Relationship(
        sa_relationship_kwargs=dict(lazy="subquery"),
        back_populates="events")
