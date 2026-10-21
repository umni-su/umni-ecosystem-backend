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
"""Модели таблиц виджетов (widgets / widget_items).

WidgetVisualOptions — визуальные опции элемента виджета. Хранятся в
widget_items.options (JSON). extra="allow": legacy-опции из старых
синхронизаций не должны ломать валидацию.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict

from entities.enums.widget_type_enum import WidgetTypeEnum


class WidgetVisualOptions(BaseModel):
    """Визуальные опции элемента виджета (widget_items.options)."""
    model_config = ConfigDict(extra="allow")

    # Какой UI-компонент рисовать (slider, switch, colorpicker, gauge, ...)
    component: Optional[str] = None
    color: Optional[str] = None
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None
    show_value: Optional[bool] = None
    unit_visible: Optional[bool] = None
    icon: Optional[str] = None


class WidgetItemModel(BaseModel):
    id: Optional[int] = None
    widget_id: Optional[int] = None
    title: Optional[str] = None
    # Для DEVICE-виджета — device_sensors.id, для CAMERA — camera_areas.id
    entity_id: Optional[int] = None
    options: Optional[dict] = None
    sort_order: int = 0


class WidgetItemCreateModel(BaseModel):
    id: Optional[int] = None
    title: Optional[str] = None
    entity_id: Optional[int] = None
    options: Optional[dict] = None
    sort_order: int = 0


class WidgetModel(BaseModel):
    id: Optional[int] = None
    title: str
    type: WidgetTypeEnum
    # Владелец: devices.id или cameras.id (определяется type)
    entity_id: int
    size: str = "md"
    active: bool = True
    sort_order: int = 0
    items: list[WidgetItemModel] = []


class WidgetCreateModel(BaseModel):
    title: str
    type: WidgetTypeEnum
    entity_id: int
    size: str = "md"
    active: bool = True
    sort_order: int = 0
    items: list[WidgetItemCreateModel] = []


class WidgetUpdateModel(WidgetCreateModel):
    pass
