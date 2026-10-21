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
from models.widget_model import WidgetCreateModel, WidgetModel, WidgetUpdateModel
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
