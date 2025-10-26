# notification_factory.py
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

from classes.notifications.notification_handler import NotificationHandler
from classes.notifications.via.email_notification_handler import EmailNotificationHandler
from classes.notifications.via.telegram_notification_handler import TelegramNotificationHandler
from entities.enums.notification_type_enum import NotificationTypeEnum


class NotificationFactory:
    """Фабрика для создания обработчиков уведомлений"""

    _handlers = {
        NotificationTypeEnum.TELEGRAM: TelegramNotificationHandler,
        NotificationTypeEnum.EMAIL: EmailNotificationHandler,
    }

    @classmethod
    def get_handler(cls, notification_type: NotificationTypeEnum) -> NotificationHandler:
        """
        Возвращает обработчик для указанного типа уведомления

        Args:
            notification_type: Тип уведомления

        Returns:
            NotificationHandler: Экземпляр обработчика

        Raises:
            ValueError: Если тип уведомления не поддерживается
        """
        handler_class = cls._handlers.get(notification_type)
        if not handler_class:
            raise ValueError(f"Unsupported notification type: {notification_type}")

        return handler_class()

    @classmethod
    def register_handler(cls, notification_type: NotificationTypeEnum, handler_class):
        """
        Регистрирует новый обработчик уведомлений

        Args:
            notification_type: Тип уведомления
            handler_class: Класс обработчика
        """
        cls._handlers[notification_type] = handler_class
