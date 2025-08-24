from typing import TYPE_CHECKING, Optional

from entities.camera import CameraEntity
from entities.enums.event_priority_enum import EventPriorityEnum
from entities.mixins.created_updated import TimeStampMixin
from entities.mixins.id_column import IdColumnMixin
from sqlmodel import Field, Relationship, Column
from sqlalchemy.types import JSON, Boolean
from sqlalchemy.sql import false

if TYPE_CHECKING:
    from entities.camera_event import CameraEventEntity


class CameraAreaEntityBase:
    camera_id: int = Field(
        nullable=False,
        index=True,
        foreign_key="cameras.id"
    )
    name: str = Field(
        nullable=False
    )
    priority: Optional[int] = Field(
        nullable=False,
        default=EventPriorityEnum.ALERT
    )
    active: bool = Field(
        sa_column=Column(
            Boolean,
            index=True,
            nullable=False,
            server_default=false())
    )
    points: list[list[int]] = Field(
        sa_column=Column(
            JSON,
            nullable=True
        )
    )
    color: str = Field(
        nullable=False,
        default='#2D90B869'
    )
    options: Optional[dict] = Field(
        sa_column=Column(
            JSON,
            nullable=True
        )
    )


class CameraAreaEntity(
    TimeStampMixin,
    CameraAreaEntityBase,
    IdColumnMixin,
    table=True
):
    __tablename__ = 'camera_areas'
    camera: CameraEntity | None = Relationship(
        # sa_relationship_kwargs=dict(lazy="selectin"),
        back_populates="areas")

    events: list["CameraEventEntity"] = Relationship(
        sa_relationship_kwargs=dict(
            # lazy="selectin",
            cascade="all, delete-orphan"
        ),
        back_populates="area",
    )
