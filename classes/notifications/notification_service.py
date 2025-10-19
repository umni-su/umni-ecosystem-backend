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

from typing import List

from classes.notifications.notification_factory import NotificationFactory
from models.notification_model import NotificationModel
from repositories.notification_repository import NotificationRepository


class NotificationService:
    """Сервис для работы с уведомлениями"""

    @staticmethod
    async def send_notification(notification_id: int, message: str, **kwargs) -> bool:
        """
        Отправляет уведомление по его ID

        Args:
            notification_id: ID уведомления
            message: Текст сообщения
            **kwargs: Дополнительные параметры

        Returns:
            bool: Результат отправки
        """
        notification = NotificationRepository.get_notification(notification_id)
        if not notification or not notification.active:
            return False

        return await NotificationService.send_to_notification(notification, message, **kwargs)

    @staticmethod
    async def send_to_notification(notification: NotificationModel, message: str, **kwargs) -> bool:
        """
        Отправляет уведомление через указанное уведомление

        Args:
            notification: Модель уведомления
            message: Текст сообщения
            **kwargs: Дополнительные параметры

        Returns:
            bool: Результат отправки
        """
        try:
            handler = NotificationFactory.get_handler(notification.type)
            return await handler.send(notification, message, **kwargs)
        except Exception as e:
            print(f"Notification service error: {e}")
            return False

    @staticmethod
    async def broadcast_message(message: str, **kwargs) -> List[bool]:
        """
        Рассылает сообщение всем активным уведомлениям

        Args:
            message: Текст сообщения
            **kwargs: Дополнительные параметры

        Returns:
            List[bool]: Результаты отправки для каждого уведомления
        """
        active_notifications = NotificationRepository.get_active_notifications()
        results = []

        for notification in active_notifications:
            result = await NotificationService.send_to_notification(notification, message, **kwargs)
            results.append(result)

        return results

    @staticmethod
    def validate_notification_config(notification_type, options: dict) -> bool:
        """
        Проверяет корректность конфигурации уведомления

        Args:
            notification_type: Тип уведомления
            options: Настройки уведомления

        Returns:
            bool: Результат валидации
        """
        try:
            handler = NotificationFactory.get_handler(notification_type)
            return handler.validate_config(options)
        except Exception:
            return False
