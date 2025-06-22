from entities.enums.camera_delete_after_enum import CameraDeleteAfterEnum
from entities.enums.camera_protocol_enum import CameraProtocolEnum
from entities.mixins.created_updated import TimeStampMixin
from entities.mixins.id_column import IdColumnMixin
from sqlmodel import SQLModel, Field, Relationship

from entities.storage import StorageEntity


class CameraEntityBase:
    name: str = Field(nullable=False)
    active: bool = Field(default=True)
    storage_id: int = Field(nullable=False, foreign_key="storages.id")
    record: bool = Field(default=False)
    record_duration: int = Field(default=5)
    delete_after: CameraDeleteAfterEnum | None = Field(default=None, nullable=True)


class CameraEntityConnection:
    protocol: CameraProtocolEnum | None = Field(default=None, nullable=True)
    ip: str = Field(nullable=False)
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
    storage: StorageEntity | None = Relationship(back_populates="cameras")
