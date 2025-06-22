from entities.mixins.created_updated import TimeStampMixin
from entities.mixins.id_column import IdColumnMixin
from sqlmodel import Field


class StorageEntityBase:
    name: str = Field(nullable=True)
    path: str = Field(nullable=True)
    active: bool = Field(default=True)


class StorageEntity(TimeStampMixin, StorageEntityBase, IdColumnMixin, table=True):
    __tablename__ = 'storages'
