# notification_queue_repository.py
#  Copyright (C) 2025 Mikhail Sazanov
#  #
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#  #
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#  #
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

from datetime import datetime
from typing import Optional, List
from sqlmodel import select, col, desc

from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from database.session import write_session
from entities.notification_queue import NotificationQueueEntity
from models.notification_queue_model import (
    NotificationQueueModel,
    NotificationQueueCreateModel,
    NotificationQueueUpdateModel
)
from repositories.base_repository import BaseRepository


class NotificationQueueRepository(BaseRepository):
    entity_class = NotificationQueueEntity
    model_class = NotificationQueueModel

    @classmethod
    def update_notifications_priority_batch(
            cls,
            notification_id: int,
            new_priority: int
    ) -> int:
        """Массовое обновление приоритета для всех элементов очереди по notification_id"""
        with write_session() as sess:
            try:
                # Находим все элементы с указанным notification_id
                statement = select(NotificationQueueEntity).where(
                    NotificationQueueEntity.notification_id == notification_id
                )
                queue_items = sess.exec(statement).all()

                if not queue_items:
                    return 0

                # Обновляем приоритет для всех найденных элементов
                updated_count = 0
                for item in queue_items:
                    item.priority = new_priority
                    sess.add(item)
                    updated_count += 1

                sess.commit()
                Logger.info(f"Updated priority for {updated_count} queue items for notification {notification_id}",
                            LoggerType.NOTIFICATIONS)
                return updated_count

            except Exception as e:
                Logger.err(str(e), LoggerType.NOTIFICATIONS)
                return 0

    @classmethod
    def get_queue_items(
            cls,
            notification_id: Optional[int] = None,
            pending_only: bool = False,
            limit: Optional[int] = None
    ) -> List[NotificationQueueModel]:
        """Получить элементы очереди с фильтрацией"""
        with write_session() as sess:
            try:
                statement = select(NotificationQueueEntity)

                statement = statement.where(
                    NotificationQueueEntity.priority > -1
                )

                if notification_id:
                    statement = statement.where(
                        NotificationQueueEntity.notification_id == notification_id
                    )

                if pending_only:
                    statement = statement.where(
                        NotificationQueueEntity.retry_count < NotificationQueueEntity.max_retries
                    )

                statement = statement.order_by(
                    desc(NotificationQueueEntity.priority),
                    col(NotificationQueueEntity.created).asc()
                )

                if limit:
                    statement = statement.limit(limit)

                queue_items = sess.exec(statement).all()
                return [
                    NotificationQueueModel.model_validate(q.to_dict())
                    for q in queue_items
                ]

            except Exception as e:
                Logger.err(str(e), LoggerType.NOTIFICATIONS)
                return []

    @classmethod
    def get_queue_item(cls, queue_id: int) -> Optional[NotificationQueueModel]:
        """Получить элемент очереди по ID"""
        with write_session() as sess:
            try:
                queue_item = sess.get(NotificationQueueEntity, queue_id)
                return NotificationQueueModel.model_validate(queue_item.to_dict()) if queue_item else None
            except Exception as e:
                Logger.err(str(e), LoggerType.NOTIFICATIONS)
                return None

    @classmethod
    def create_queue_item(cls, model: NotificationQueueCreateModel) -> Optional[NotificationQueueModel]:
        """Создать новый элемент очереди"""
        with write_session() as sess:
            try:
                queue_item = NotificationQueueEntity(
                    notification_id=model.notification_id,
                    to=model.to,
                    subject=model.subject,
                    message=model.message,
                    priority=model.priority,
                    max_retries=model.max_retries,
                    options=model.options
                )

                sess.add(queue_item)
                sess.commit()
                sess.refresh(queue_item)
                return NotificationQueueModel.model_validate(queue_item.to_dict())

            except Exception as e:
                Logger.err(str(e), LoggerType.NOTIFICATIONS)
                return None

    @classmethod
    def update_queue_item(
            cls,
            model: NotificationQueueModel
    ) -> Optional[NotificationQueueModel]:
        """Обновить элемент очереди"""
        with write_session() as sess:
            try:
                queue_item = sess.get(NotificationQueueEntity, model.id)
                if not queue_item:
                    return None

                # Обновляем только переданные поля
                if model.to is not None:
                    queue_item.to = model.to
                if model.subject is not None:
                    queue_item.subject = model.subject
                if model.message is not None:
                    queue_item.message = model.message
                if model.priority is not None:
                    queue_item.priority = model.priority
                if model.retry_count is not None:
                    queue_item.retry_count = model.retry_count
                if model.max_retries is not None:
                    queue_item.max_retries = model.max_retries
                if model.last_attempt is not None:
                    queue_item.last_attempt = model.last_attempt
                if model.options is not None:
                    queue_item.options = model.options

                sess.add(queue_item)
                sess.commit()
                sess.refresh(queue_item)
                return NotificationQueueModel.model_validate(queue_item.to_dict())

            except Exception as e:
                Logger.err(str(e), LoggerType.NOTIFICATIONS)
                return None

    @classmethod
    def update_queue_attempt(
            cls,
            queue_id: int,
            retry_count: int,
            last_attempt: Optional[datetime] = None
    ) -> Optional[NotificationQueueModel]:
        """Обновить счетчик попыток и время последней попытки"""
        update_model = NotificationQueueUpdateModel(
            retry_count=retry_count,
            last_attempt=last_attempt or datetime.now()
        )
        return cls.update_queue_item(queue_id, update_model)

    @classmethod
    def delete_queue_item(cls, queue_id: int) -> bool:
        """Удалить элемент очереди"""
        with write_session() as sess:
            try:
                queue_item = sess.get(NotificationQueueEntity, queue_id)
                if not queue_item:
                    return False

                sess.delete(queue_item)
                sess.commit()
                return True

            except Exception as e:
                Logger.err(str(e), LoggerType.NOTIFICATIONS)
                return False

    @classmethod
    def reset_retry_count(
            cls,
            queue_id: Optional[int] = None,
            notification_id: Optional[int] = None
    ) -> int:
        """Сбросить счетчик попыток для неудачных элементов"""
        with write_session() as sess:
            try:
                statement = select(NotificationQueueEntity).where(
                    NotificationQueueEntity.retry_count >= NotificationQueueEntity.max_retries
                )

                if queue_id:
                    statement = statement.where(NotificationQueueEntity.id == queue_id)
                elif notification_id:
                    statement = statement.where(NotificationQueueEntity.notification_id == notification_id)

                failed_items = sess.exec(statement).all()

                for item in failed_items:
                    item.retry_count = 0
                    item.last_attempt = None
                    sess.add(item)

                sess.commit()
                return len(failed_items)

            except Exception as e:
                Logger.err(str(e), LoggerType.NOTIFICATIONS)
                return 0

    @classmethod
    def get_queue_stats(cls) -> dict:
        """Получить статистику очереди"""
        with write_session() as sess:
            try:
                # Общее количество
                total_stmt = select(NotificationQueueEntity)
                total_count = len(sess.exec(total_stmt).all())

                # Ожидающие обработки
                pending_stmt = select(NotificationQueueEntity).where(
                    NotificationQueueEntity.retry_count < NotificationQueueEntity.max_retries
                )
                pending_count = len(sess.exec(pending_stmt).all())

                # Неудачные
                failed_count = total_count - pending_count

                # По приоритетам
                high_count = len(sess.exec(
                    select(NotificationQueueEntity).where(NotificationQueueEntity.priority == 2)
                ).all())

                medium_count = len(sess.exec(
                    select(NotificationQueueEntity).where(NotificationQueueEntity.priority == 1)
                ).all())

                low_count = len(sess.exec(
                    select(NotificationQueueEntity).where(NotificationQueueEntity.priority == 0)
                ).all())

                return {
                    "total": total_count,
                    "pending": pending_count,
                    "failed": failed_count,
                    "by_priority": {
                        "high": high_count,
                        "medium": medium_count,
                        "low": low_count,
                    }
                }

            except Exception as e:
                Logger.err(str(e), LoggerType.NOTIFICATIONS)
                return {}

    @classmethod
    def cleanup_old_items(cls, days: int = 30) -> int:
        """Очистить старые элементы очереди"""
        with write_session() as sess:
            try:
                from datetime import timedelta
                cutoff_date = datetime.now() - timedelta(days=days)

                statement = select(NotificationQueueEntity).where(
                    NotificationQueueEntity.created < cutoff_date
                )
                old_items = sess.exec(statement).all()
                deleted_count = len(old_items)

                for item in old_items:
                    sess.delete(item)

                sess.commit()
                return deleted_count

            except Exception as e:
                Logger.err(str(e), LoggerType.NOTIFICATIONS)
                return 0

    @classmethod
    def get_items_for_processing(cls, batch_size: int = 10) -> List[NotificationQueueModel]:
        """Получить элементы для обработки"""
        return cls.get_queue_items(pending_only=True, limit=batch_size)
