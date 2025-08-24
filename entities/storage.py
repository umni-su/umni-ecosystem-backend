from typing import TYPE_CHECKING
from entities.mixins.created_updated import TimeStampMixin
from entities.mixins.id_column import IdColumnMixin
from sqlmodel import Field, Relationship

if TYPE_CHECKING:
    from entities.camera import CameraEntity


class StorageEntityBase:
    name: str = Field(
        nullable=True
    )
    path: str = Field(
        unique=True,
        nullable=True
    )
    active: bool = Field(
        index=True,
        default=True
    )


class StorageEntity(
    TimeStampMixin,
    StorageEntityBase,
    IdColumnMixin,
    table=True
):
    __tablename__ = 'storages'
    cameras: list["CameraEntity"] = Relationship(
        sa_relationship_kwargs=dict(
            # lazy="selectin"
        ),
        back_populates="storage"
    )
