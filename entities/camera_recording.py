from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlmodel import Field, Relationship

from entities.mixins.created_updated import TimeStampMixin
from entities.mixins.id_column import IdColumnMixin

if TYPE_CHECKING:
    from entities.camera import CameraEntity
    from entities.camera_event import CameraEventEntity


class CameraRecordingEntity(
    TimeStampMixin,
    IdColumnMixin,
    table=True
):
    __tablename__ = "camera_recordings"

    camera_id: int = Field(
        index=True,
        foreign_key="cameras.id"
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
    duration: Optional[float] = None
    path: Optional[str] = None

    camera: "CameraEntity" = Relationship(
        # sa_relationship_kwargs=dict(lazy="selectin"),
        back_populates="recordings")

    events: list["CameraEventEntity"] = Relationship(
        sa_relationship_kwargs=dict(
            # lazy="selectin",
            cascade="all, delete-orphan"
        ),
        back_populates="recording"
    )
