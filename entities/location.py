from typing import TYPE_CHECKING

from entities.mixins.created_updated import TimeStampMixin
from entities.mixins.id_column import IdColumnMixin
from sqlmodel import Field, Relationship

if TYPE_CHECKING:
    from entities.camera import CameraEntity


class LocationEntityBase:
    name: str = Field(
        nullable=False
    )
    long: float | None = Field(
        nullable=True,
        default=None
    )
    lat: float | None = Field(
        nullable=True, default=None
    )


class LocationEntity(
    TimeStampMixin,
    LocationEntityBase,
    IdColumnMixin,
    table=True
):
    __tablename__ = 'locations'

    cameras: list["CameraEntity"] = Relationship(
        back_populates="location"
    )
