# notification_repository.py
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

from sqlmodel import select, col
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from database.session import write_session
from entities.notification import NotificationEntity
from models.notification_model import NotificationModel
from repositories.base_repository import BaseRepository
from repositories.notification_queue_repository import NotificationQueueRepository


class NotificationRepository(BaseRepository):
    entity_class = NotificationEntity
    model_class = NotificationModel

    @classmethod
    def get_notifications(cls):
        with write_session() as sess:
            try:
                notifications_orm = sess.exec(
                    select(NotificationEntity).order_by(
                        col(NotificationEntity.id).desc()
                    )
                ).all()
                return [
                    NotificationModel.model_validate(
                        n.to_dict()
                    )
                    for n in notifications_orm
                ]
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)
                return []

    @classmethod
    def get_notification(cls, notification_id: int) -> NotificationModel | None:
        with write_session() as sess:
            try:
                notification_orm = sess.get(NotificationEntity, notification_id)
                if not notification_orm:
                    return None
                return NotificationModel.model_validate(
                    notification_orm.to_dict()
                )
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)
                return None

    @classmethod
    def create_notification(cls, model: NotificationModel) -> NotificationModel | None:
        with write_session() as sess:
            try:
                notification_entity = NotificationEntity()
                notification_entity.name = model.name
                notification_entity.type = model.type.value
                notification_entity.active = model.active
                notification_entity.options = model.options.model_dump() if model.options else None

                sess.add(notification_entity)
                sess.commit()
                sess.refresh(notification_entity)

                return NotificationModel.model_validate(
                    notification_entity.to_dict()
                )
            except Exception as e:
                Logger.err(str(e), LoggerType.NOTIFICATIONS)
                return None

    @classmethod
    def update_notification(cls, notification_id: int, model: NotificationModel) -> NotificationModel | None:
        with write_session() as sess:
            try:
                notification_entity = sess.get(NotificationEntity, notification_id)
                if not notification_entity:
                    return None

                # Получаем текущие options из БД
                current_options = notification_entity.options or {}

                # Обрабатываем sensitive поля
                processed_options = cls._process_sensitive_fields(
                    model.options.model_dump() if model.options else {},
                    current_options
                )

                notification_entity.name = model.name
                notification_entity.type = model.type.value
                notification_entity.active = model.active
                notification_entity.options = processed_options

                sess.add(notification_entity)
                sess.commit()
                sess.refresh(notification_entity)

                # Обновляем приоритет для уведомлений при смене статуса активности. -1 - уведомления не попадут в выборку в сервисе
                NotificationQueueRepository.update_notifications_priority_batch(
                    notification_id=notification_entity.id,
                    new_priority=2 if notification_entity.active else -1,
                )

                return NotificationModel.model_validate(
                    notification_entity.to_dict()
                )
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)
                return None

    @classmethod
    def _process_sensitive_fields(cls, new_options: dict, current_options: dict) -> dict:
        """Обрабатываем sensitive поля: сохраняем зашифрованные значения если не изменились"""
        result = new_options.copy()

        # Здесь можно добавить логику для определения sensitive полей
        # Пока просто проверяем зашифрованные значения
        for key, value in new_options.items():
            current_value = current_options.get(key)

            # Если новое значение - маска или равно текущему зашифрованному
            if (current_value and
                    isinstance(current_value, str) and
                    current_value.startswith('gAAAAA') and
                    (value == '********' or value == current_value)):
                # Сохраняем оригинальное зашифрованное значение
                result[key] = current_value

        return result

    @classmethod
    def delete_notification(cls, notification_id: int) -> bool:
        with write_session() as sess:
            try:
                notification_entity = sess.get(NotificationEntity, notification_id)
                if not notification_entity:
                    return False

                sess.delete(notification_entity)
                sess.commit()
                return True
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)
                return False

    @classmethod
    def get_active_notifications(cls):
        with write_session() as sess:
            try:
                notifications_orm = sess.exec(
                    select(NotificationEntity).where(
                        NotificationEntity.active == True
                    )
                ).all()
                return [
                    NotificationModel.model_validate(
                        n.to_dict()
                    )
                    for n in notifications_orm
                ]
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)
                return []
