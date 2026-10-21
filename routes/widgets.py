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

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException

from classes.auth.auth import Auth
from classes.l10n.l10n import _
from entities.enums.widget_type_enum import WidgetTypeEnum
from models.widget_model import WidgetCreateModel, WidgetItemCreateModel, \
    WidgetItemModel, WidgetItemReorderModel, WidgetModel, WidgetUpdateModel
from repositories.widget_repository import WidgetRepository
from responses.user import UserResponseOut

widgets = APIRouter(
    prefix='/widgets',
    tags=['widgets']
)


@widgets.get('', response_model=list[WidgetModel])
def get_widgets(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        entity_id: Optional[int] = None,
        type: Optional[WidgetTypeEnum] = None,
):
    """Список виджетов; фильтр по владельцу (device_id/camera_id) и типу."""
    return WidgetRepository.get_widgets(entity_id=entity_id, widget_type=type)


@widgets.get('/{widget_id}', response_model=WidgetModel)
def get_widget(
        widget_id: int,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    widget = WidgetRepository.get_widget(widget_id)
    if widget is None:
        raise HTTPException(status_code=404, detail=_('Widget not found'))
    return widget


@widgets.post('', response_model=WidgetModel)
def create_widget(
        model: WidgetCreateModel,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    widget = WidgetRepository.create_widget(model)
    if widget is None:
        raise HTTPException(status_code=400, detail=_('Error creating widget'))
    return widget


@widgets.put('/{widget_id}', response_model=WidgetModel)
def update_widget(
        widget_id: int,
        model: WidgetUpdateModel,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    """Обновить виджет; items перезаписываются целиком."""
    widget = WidgetRepository.update_widget(widget_id, model)
    if widget is None:
        raise HTTPException(status_code=404, detail=_('Widget not found'))
    return widget


@widgets.patch('/{widget_id}/sort', response_model=WidgetModel)
def update_widget_sort(
        widget_id: int,
        sort_order: int,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    widget = WidgetRepository.update_widget_order(widget_id, sort_order)
    if widget is None:
        raise HTTPException(status_code=404, detail=_('Widget not found'))
    return widget


@widgets.delete('/{widget_id}')
def delete_widget(
        widget_id: int,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    if not WidgetRepository.delete_widget(widget_id):
        raise HTTPException(status_code=404, detail=_('Widget not found'))
    return {"success": True}


# ========== Items ==========
# Литеральный путь /items/reorder объявлен выше /items/{item_id}:
# Starlette матчит по порядку регистрации, иначе "reorder" съедается
# как item_id и запрос падает с 422.


@widgets.get('/{widget_id}/items', response_model=list[WidgetItemModel])
def get_widget_items(
        widget_id: int,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    """Список items виджета (по sort_order)."""
    items = WidgetRepository.get_widget_items(widget_id)
    if items is None:
        raise HTTPException(status_code=404, detail=_('Widget not found'))
    return items


@widgets.post('/{widget_id}/items', response_model=WidgetItemModel)
def create_widget_item(
        widget_id: int,
        model: WidgetItemCreateModel,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    """Добавить item; sort_order назначается max+1, если не передан.

    Items поддерживаются только у DEVICE-виджетов; entity_id должен
    указывать на сенсор устройства-владельца виджета.
    """
    return WidgetRepository.create_item(widget_id, model)


@widgets.put('/{widget_id}/items/reorder', response_model=list[WidgetItemModel])
def reorder_widget_items(
        widget_id: int,
        items: list[WidgetItemReorderModel],
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    """Bulk-reorder: [{"id": 1, "sort_order": 0}, ...]; атомарно."""
    return WidgetRepository.reorder_items(widget_id, items)


@widgets.put('/{widget_id}/items/{item_id}', response_model=WidgetItemModel)
def update_widget_item(
        widget_id: int,
        item_id: int,
        model: WidgetItemCreateModel,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    """Изменить item (title, entity_id, options, sort_order)."""
    return WidgetRepository.update_item(widget_id, item_id, model)


@widgets.delete('/{widget_id}/items/{item_id}')
def delete_widget_item(
        widget_id: int,
        item_id: int,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    if not WidgetRepository.delete_item(widget_id, item_id):
        raise HTTPException(status_code=404, detail=_('Widget item not found'))
    return {"success": True}
