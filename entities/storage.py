from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from entities.camera import CameraEntity
from entities.mixins.created_updated import TimeStampMixin
from entities.mixins.id_column import IdColumnMixin
from sqlmodel import Field, Relationship


class StorageEntityBase:
    name: str = Field(nullable=True)
    path: str = Field(nullable=True)
    active: bool = Field(default=True)


class StorageEntity(TimeStampMixin, StorageEntityBase, IdColumnMixin, table=True):
    __tablename__ = 'storages'
    cameras: list["CameraEntity"] = Relationship(back_populates="storage")
