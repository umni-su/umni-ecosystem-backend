from entities.camera_recording import CameraRecordingEntity
from entities.storage import StorageEntity
from entities.enums.camera_protocol_enum import CameraProtocolEnum
from entities.enums.camera_record_type_enum import CameraRecordTypeEnum
from entities.mixins.created_updated import TimeStampMixin
from entities.mixins.id_column import IdColumnMixin
from sqlmodel import Field, Relationship
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from entities.camera_area import CameraAreaEntity
    from entities.camera_event import CameraEventEntity


class CameraEntityBase:
    name: str = Field(
        nullable=False
    )
    active: bool = Field(
        default=True,
        index=True)
    storage_id: int = Field(
        index=True,
        nullable=False,
        foreign_key="storages.id"
    )
    location_id: int | None = Field(
        index=True,
        nullable=True,
        foreign_key="locations.id"
    )
    record: bool = Field(
        default=False,
        index=True
    )
    record_mode: Optional[int] = Field(
        default=CameraRecordTypeEnum.DETECTION_VIDEO
    )
    record_duration: Optional[int] = Field(
        default=None
    )
    delete_after: Optional[int] = Field(
        default=None
    )
    cover: Optional[str] = Field(
        default=None,
        max_length=255
    )
    fps: Optional[int] = Field(
        default=None
    )
    scale: Optional[float] = Field(
        default=None
    )
    alerts: bool = Field(
        default=False,
        index=True
    )


class CameraEntityConnection:
    protocol: Optional[str] | None = Field(
        default=None,
        nullable=True
    )
    ip: str | None = Field(
        nullable=True
    )
    port: int = Field(
        nullable=False
    )
    username: str | None = Field(
        nullable=True,
        default=None
    )
    password: str | None = Field(
        nullable=True,
        default=None
    )
    primary: str | None = Field(
        nullable=True,
        default=None
    )
    secondary: str | None = Field(
        nullable=True,
        default=None
    )


class CameraEntity(
    TimeStampMixin,
    CameraEntityConnection,
    CameraEntityBase,
    IdColumnMixin,
    table=True
):
    __tablename__ = 'cameras'
    storage: StorageEntity | None = Relationship(
        # sa_relationship_kwargs=dict(lazy="selectin"),
        back_populates="cameras"
    )

    areas: list["CameraAreaEntity"] = Relationship(
        # sa_relationship_kwargs=dict(lazy="selectin"),
        back_populates="camera")

    events: list["CameraEventEntity"] = Relationship(
        sa_relationship_kwargs=dict(
            # lazy="subquery",
            cascade="all, delete-orphan"
        ),
        back_populates="camera")

    recordings: list["CameraRecordingEntity"] = Relationship(
        sa_relationship_kwargs=dict(
            # lazy="selectin",
            cascade="all, delete-orphan"
        ),
        back_populates="camera")
