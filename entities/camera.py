from entities.storage import StorageEntity
from entities.enums.camera_protocol_enum import CameraProtocolEnum
from entities.enums.camera_record_type_enum import CameraRecordTypeEnum
from entities.mixins.created_updated import TimeStampMixin
from entities.mixins.id_column import IdColumnMixin
from sqlmodel import Field, Relationship, Column
from sqlalchemy.sql import false
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from entities.camera_area import CameraAreaEntity
    from entities.camera_event import CameraEventEntity


class CameraEntityBase:
    name: str = Field(nullable=False)
    active: bool = Field(default=True)
    storage_id: int = Field(nullable=False, foreign_key="storages.id")
    location_id: int | None = Field(nullable=True, foreign_key="locations.id")
    record: bool = Field(default=False)
    record_mode: CameraRecordTypeEnum = Field(nullable=True, default=CameraRecordTypeEnum.DETECTION_VIDEO)
    record_duration: int | None = Field(sa_column=Column(nullable=True, default=None))
    delete_after: int | None = Field(default=None, nullable=True)
    cover: None | str = Field(nullable=True, default=None)
    fps: int | None = Field(nullable=True)
    scale: float | None = Field(nullable=True)
    alerts: bool = Field(sa_column=Column(nullable=False, server_default=false()))


class CameraEntityConnection:
    protocol: CameraProtocolEnum | None = Field(default=None, nullable=True)
    ip: str | None = Field(nullable=True)
    port: int = Field(nullable=False)
    username: str | None = Field(nullable=True, default=None)
    password: str | None = Field(nullable=True, default=None)
    primary: str | None = Field(nullable=True, default=None)
    secondary: str | None = Field(nullable=True, default=None)


class CameraEntity(
    TimeStampMixin,
    CameraEntityConnection,
    CameraEntityBase,
    IdColumnMixin,
    table=True):
    __tablename__ = 'cameras'
    storage: StorageEntity | None = Relationship(
        sa_relationship_kwargs=dict(lazy="subquery"),
        back_populates="cameras"
    )

    areas: list["CameraAreaEntity"] = Relationship(
        sa_relationship_kwargs=dict(lazy="subquery"),
        back_populates="camera")

    events: list["CameraEventEntity"] = Relationship(
        sa_relationship_kwargs=dict(lazy="subquery"),
        back_populates="camera")
