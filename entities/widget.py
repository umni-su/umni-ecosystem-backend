#  Copyright (C) 2026 Mikhail Sazanov
#  #
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column
from sqlmodel import Field, Relationship

from entities.enums.widget_type_enum import WidgetTypeEnum
from entities.mixins.created_updated import TimeStampMixin
from entities.mixins.id_column import IdColumnMixin

if TYPE_CHECKING:
    from entities.widget_item import WidgetItemEntity


class WidgetBase:
    title: str = Field(
        index=True
    )
    # Полиморфный владелец: DEVICE -> devices.id, CAMERA -> cameras.id.
    # Реального FK нет (владелец один на два типа), поэтому только индекс.
    type: WidgetTypeEnum = Field(
        index=True,
        description="WidgetTypeEnum: определяет сущность для entity_id"
    )
    entity_id: int = Field(
        index=True,
        description="Владелец виджета: devices.id или cameras.id"
    )
    size: str = Field(
        default="md",
        description="Размерный класс (WidgetSizeEnum: sm, md, lg, full)"
    )
    active: bool = Field(
        default=True
    )
    sort_order: int = Field(
        default=0
    )


class WidgetEntity(
    TimeStampMixin,
    WidgetBase,
    IdColumnMixin,
    table=True
):
    __tablename__ = 'widgets'

    items: list["WidgetItemEntity"] = Relationship(
        back_populates="widget",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "WidgetItemEntity.sort_order",
            "passive_deletes": True
        }
    )

    def __repr__(self):
        return f"<Widget {self.id} {self.title} ({self.type.value}:{self.entity_id})>"
