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

from typing import Optional

from sqlalchemy.orm import selectinload
from sqlmodel import select, col

from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from database.session import write_session, read_session
from entities.enums.widget_type_enum import WidgetTypeEnum
from entities.widget import WidgetEntity
from entities.widget_item import WidgetItemEntity
from models.widget_model import WidgetCreateModel, WidgetModel, WidgetUpdateModel
from repositories.base_repository import BaseRepository


class WidgetRepository(BaseRepository):
    entity_class = WidgetEntity
    model_class = WidgetModel

    # ========== Чтение ==========

    @classmethod
    def _to_model(cls, widget: WidgetEntity) -> WidgetModel:
        return WidgetModel.model_validate(
            widget.to_dict(include_relationships=True)
        )

    @classmethod
    def _load_options(cls):
        """Жадная загрузка items (иначе выборка вне сессии упадёт)."""
        return selectinload(WidgetEntity.items)

    @classmethod
    def get_widgets(
            cls,
            entity_id: Optional[int] = None,
            widget_type: Optional[WidgetTypeEnum] = None,
    ) -> list[WidgetModel]:
        """Список виджетов; можно отфильтровать по владельцу и/или типу."""
        with read_session() as sess:
            try:
                q = select(WidgetEntity).options(cls._load_options())
                if entity_id is not None:
                    q = q.where(col(WidgetEntity.entity_id) == entity_id)
                if widget_type is not None:
                    q = q.where(col(WidgetEntity.type) == widget_type.value)
                q = q.order_by(
                    col(WidgetEntity.sort_order).asc(),
                    col(WidgetEntity.id).asc(),
                )
                widgets_orm = sess.exec(q).all()
                return [cls._to_model(w) for w in widgets_orm]
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)
                return []

    @classmethod
    def get_widget(cls, widget_id: int) -> Optional[WidgetModel]:
        with read_session() as sess:
            try:
                q = (
                    select(WidgetEntity)
                    .where(col(WidgetEntity.id) == widget_id)
                    .options(cls._load_options())
                )
                widget_orm = sess.exec(q).first()
                if widget_orm is not None:
                    return cls._to_model(widget_orm)
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)
        return None

    # ========== Запись ==========

    @classmethod
    def _sync_items(cls, widget: WidgetEntity, items) -> None:
        """Перезаписать items виджета (полная замена списка)."""
        widget.items.clear()
        for item_data in items or []:
            widget.items.append(
                WidgetItemEntity(
                    title=item_data.title,
                    entity_id=item_data.entity_id,
                    options=item_data.options,
                    sort_order=item_data.sort_order,
                )
            )

    @classmethod
    def create_widget(cls, model: WidgetCreateModel) -> Optional[WidgetModel]:
        with write_session() as sess:
            try:
                widget = WidgetEntity(
                    title=model.title,
                    type=model.type,
                    entity_id=model.entity_id,
                    size=model.size,
                    active=model.active,
                    sort_order=model.sort_order,
                )
                cls._sync_items(widget, model.items)
                sess.add(widget)
                sess.commit()
                sess.refresh(widget)
                return cls._to_model(widget)
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)
                return None

    @classmethod
    def update_widget(
            cls,
            widget_id: int,
            model: WidgetUpdateModel,
    ) -> Optional[WidgetModel]:
        with write_session() as sess:
            try:
                widget = sess.get(WidgetEntity, widget_id)
                if widget is None:
                    return None
                widget.title = model.title
                widget.type = model.type
                widget.entity_id = model.entity_id
                widget.size = model.size
                widget.active = model.active
                widget.sort_order = model.sort_order
                cls._sync_items(widget, model.items)
                sess.add(widget)
                sess.commit()
                sess.refresh(widget)
                return cls._to_model(widget)
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)
                return None

    @classmethod
    def update_widget_order(cls, widget_id: int, sort_order: int) -> Optional[WidgetModel]:
        """Обновить только порядок виджета."""
        with write_session() as sess:
            try:
                widget = sess.get(WidgetEntity, widget_id)
                if widget is None:
                    return None
                widget.sort_order = sort_order
                sess.add(widget)
                sess.commit()
                sess.refresh(widget)
                return cls._to_model(widget)
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)
                return None

    @classmethod
    def delete_widget(cls, widget_id: int) -> bool:
        with write_session() as sess:
            try:
                widget = sess.get(WidgetEntity, widget_id)
                if widget is None:
                    return False
                # Items удалятся автоматически благодаря каскаду
                sess.delete(widget)
                sess.commit()
                return True
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)
                return False
