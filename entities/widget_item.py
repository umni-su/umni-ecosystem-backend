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

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship

from entities.mixins.created_updated import TimeStampMixin
from entities.mixins.id_column import IdColumnMixin

if TYPE_CHECKING:
    from entities.widget import WidgetEntity


class WidgetItemBase:
    widget_id: int | None = Field(
        default=None,
        index=True,
        foreign_key="widgets.id",
        ondelete="CASCADE"
    )
    title: str | None = Field(
        nullable=True
    )
    # Что отображается в элементе: для DEVICE-виджета — device_sensors.id,
    # для CAMERA — например camera_areas.id. Полиморфный, без FK.
    entity_id: int | None = Field(
        default=None,
        index=True
    )
    # WidgetVisualOptions (component, color, min/max, step, show_value, ...)
    options: Optional[dict] = Field(
        sa_column=Column(
            JSON, nullable=True
        )
    )
    sort_order: int = Field(
        default=0
    )


class WidgetItemEntity(
    TimeStampMixin,
    WidgetItemBase,
    IdColumnMixin,
    table=True
):
    __tablename__ = 'widget_items'

    widget: Optional["WidgetEntity"] = Relationship(
        back_populates="items"
    )

    def __repr__(self):
        return f"<WidgetItem {self.id} widget={self.widget_id} entity={self.entity_id}>"
