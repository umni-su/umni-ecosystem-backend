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

from fastapi import HTTPException
from sqlalchemy.orm import selectinload
from sqlmodel import select, col

from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from database.session import write_session, read_session
from entities.enums.widget_type_enum import WidgetTypeEnum
from entities.sensor_entity import SensorEntity
from entities.widget import WidgetEntity
from entities.widget_item import WidgetItemEntity
from models.widget_model import WidgetCreateModel, WidgetItemCreateModel, \
    WidgetItemModel, WidgetItemReorderModel, WidgetModel, WidgetUpdateModel
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
    def _sync_items(cls, widget: WidgetEntity, items: list[WidgetItemCreateModel]) -> None:
        """Перезаписать items виджета (полная замена списка)."""
        for index, item_data in enumerate(items or []):
            if item_data.id:
                existing_index = next((i for i, itm in enumerate(widget.items) if itm.id == item_data.id), None)
                if existing_index > -1:
                    widget.items[existing_index].title = item_data.title
                    widget.items[existing_index].options = item_data.options
                    widget.items[existing_index].sort_order = index
            else:
                widget.items.append(
                    WidgetItemEntity(
                        title=item_data.title,
                        entity_id=item_data.entity_id,
                        options=item_data.options,
                        sort_order=(
                            item_data.sort_order
                            if item_data.sort_order is not None
                            else index
                        ),
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

    # ========== Items ==========

    @classmethod
    def _item_to_model(cls, item: WidgetItemEntity) -> WidgetItemModel:
        return WidgetItemModel.model_validate(item.to_dict())

    @classmethod
    def _get_widget_orm(cls, sess, widget_id: int) -> WidgetEntity:
        widget = sess.get(WidgetEntity, widget_id)
        if widget is None:
            raise HTTPException(status_code=404, detail='Widget not found')
        return widget

    @classmethod
    def _validate_item_entity(
            cls,
            sess,
            widget: WidgetEntity,
            entity_id: Optional[int],
    ) -> None:
        """Проверить, что entity_id item'а указывает на сущность владельца.

        Items поддерживаются только у DEVICE-виджетов: entity_id должен
        указывать на сенсор, принадлежащий device_id виджета.
        """
        if widget.type != WidgetTypeEnum.DEVICE:
            raise HTTPException(
                status_code=400,
                detail='Widget items are supported only for DEVICE widgets',
            )
        if entity_id is None:
            return
        sensor = sess.exec(
            select(SensorEntity).where(col(SensorEntity.id) == entity_id)
        ).first()
        if sensor is None or sensor.device_id != widget.entity_id:
            raise HTTPException(
                status_code=400,
                detail=f'Sensor {entity_id} does not belong to device {widget.entity_id}',
            )

    @classmethod
    def get_widget_items(cls, widget_id: int) -> Optional[list[WidgetItemModel]]:
        with read_session() as sess:
            try:
                widget = sess.get(WidgetEntity, widget_id)
                if widget is None:
                    return None
                q = (
                    select(WidgetItemEntity)
                    .where(col(WidgetItemEntity.widget_id) == widget_id)
                    .order_by(
                        col(WidgetItemEntity.sort_order).asc(),
                        col(WidgetItemEntity.id).asc(),
                    )
                )
                items_orm = sess.exec(q).all()
                return [cls._item_to_model(i) for i in items_orm]
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)
                return None

    @classmethod
    def create_item(
            cls,
            widget_id: int,
            model: WidgetItemCreateModel,
    ) -> WidgetItemModel:
        """Добавить item; sort_order = max+1, если не передан."""
        with write_session() as sess:
            widget = cls._get_widget_orm(sess, widget_id)
            cls._validate_item_entity(sess, widget, model.entity_id)

            if model.sort_order is None:
                last = sess.exec(
                    select(WidgetItemEntity)
                    .where(col(WidgetItemEntity.widget_id) == widget_id)
                    .order_by(col(WidgetItemEntity.sort_order).desc())
                ).first()
                model.sort_order = (last.sort_order + 1) if last else 0

            item = WidgetItemEntity(
                widget_id=widget_id,
                title=model.title,
                entity_id=model.entity_id,
                options=model.options,
                sort_order=model.sort_order,
            )
            sess.add(item)
            sess.commit()
            sess.refresh(item)
            return cls._item_to_model(item)

    @classmethod
    def update_item(
            cls,
            widget_id: int,
            item_id: int,
            model: WidgetItemCreateModel,
    ) -> WidgetItemModel:
        """Изменить item; поиск строго по паре (widget_id, item_id)."""
        with write_session() as sess:
            widget = cls._get_widget_orm(sess, widget_id)
            item = sess.exec(
                select(WidgetItemEntity)
                .where(col(WidgetItemEntity.id) == item_id)
                .where(col(WidgetItemEntity.widget_id) == widget_id)
            ).first()
            if item is None:
                raise HTTPException(status_code=404, detail='Widget item not found')

            cls._validate_item_entity(sess, widget, model.entity_id)
            item.title = model.title
            item.entity_id = model.entity_id
            item.options = model.options
            if model.sort_order is not None:
                item.sort_order = model.sort_order
            sess.add(item)
            sess.commit()
            sess.refresh(item)
            return cls._item_to_model(item)

    @classmethod
    def delete_item(cls, widget_id: int, item_id: int) -> bool:
        with write_session() as sess:
            item = sess.exec(
                select(WidgetItemEntity)
                .where(col(WidgetItemEntity.id) == item_id)
                .where(col(WidgetItemEntity.widget_id) == widget_id)
            ).first()
            if item is None:
                return False
            sess.delete(item)
            sess.commit()
            return True

    @classmethod
    def reorder_items(
            cls,
            widget_id: int,
            items: list[WidgetItemReorderModel],
    ) -> list[WidgetItemModel]:
        """Batch-обновление порядка items в одной сессии (атомарно).

        Все id должны принадлежать виджету, иначе откат всего запроса.
        """
        with write_session() as sess:
            widget = cls._get_widget_orm(sess, widget_id)

            items_orm = sess.exec(
                select(WidgetItemEntity)
                .where(col(WidgetItemEntity.widget_id) == widget_id)
            ).all()
            by_id = {i.id: i for i in items_orm}

            requested_ids = [r.id for r in items]
            if len(set(requested_ids)) != len(requested_ids) or \
                    any(i not in by_id for i in requested_ids):
                raise HTTPException(
                    status_code=400,
                    detail='Reorder payload must contain unique item ids of this widget',
                )

            for r in items:
                by_id[r.id].sort_order = r.sort_order
            sess.add_all(items_orm)
            sess.commit()

            for i in items_orm:
                sess.refresh(i)
            items_orm.sort(key=lambda i: (i.sort_order, i.id))
            return [cls._item_to_model(i) for i in items_orm]
