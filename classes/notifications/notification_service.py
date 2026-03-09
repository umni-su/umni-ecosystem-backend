# notification_service.py
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

from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from classes.notifications.notification_factory import NotificationFactory
from models.notification_model import NotificationModel
from models.notification_queue_model import NotificationQueueModel
from repositories.notification_repository import NotificationRepository


class NotificationService:
    """Сервис для работы с уведомлениями"""

    @staticmethod
    async def send_notification(
            notification_queue: NotificationQueueModel,
            **kwargs
    ) -> bool:
        """
        Отправляет уведомление по его ID

        Returns:
            bool: Результат отправки
        """
        notification = NotificationRepository.get_notification(notification_queue.notification_id)
        if not notification or not notification.active:
            Logger.warn(f'🔊 Notification {notification.id} is not active, skipping', LoggerType.NOTIFICATIONS)
            return False

        return await NotificationService.send_to_notification(
            notification=notification,
            notification_queue=notification_queue,
            **kwargs)

    @staticmethod
    async def send_to_notification(
            notification_queue: NotificationQueueModel,
            notification: NotificationModel,
            **kwargs
    ) -> bool:
        """
        Отправляет уведомление через указанное уведомление

        Returns:
            bool: Результат отправки
        """
        try:
            handler = NotificationFactory.get_handler(notification.type)
            if not handler:
                Logger.err(f'🔊 Handler for notification type {notification.type} not found', LoggerType.NOTIFICATIONS)
                return False

            if not notification.active:
                Logger.warn(f'🔊 Notification {notification.id} is not active, skipping', LoggerType.NOTIFICATIONS)
                return False

            return await handler.send(
                notification=notification,
                notification_queue=notification_queue,
                **kwargs
            )
        except Exception as e:
            Logger.err(f"Notification service error: {e}", LoggerType.NOTIFICATIONS)
            return False

    @staticmethod
    def validate_notification_config(notification_type, options: dict) -> bool:
        """
        Проверяет корректность конфигурации уведомления

        Args:
            notification_type: Тип уведомления (ID)
            options: Настройки уведомления

        Returns:
            bool: Результат валидации
        """
        return NotificationFactory.validate_notification_config(notification_type, options)

    @staticmethod
    def get_all_notification_types():
        """Возвращает все доступные типы уведомлений"""
        return NotificationFactory.get_all_notifications()
