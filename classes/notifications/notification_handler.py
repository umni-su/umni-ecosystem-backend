# notification_handler.py
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

from abc import ABC, abstractmethod
from typing import Any, Dict
from models.notification_model import NotificationModel
from models.notification_queue_model import NotificationQueueModel


class NotificationHandler(ABC):
    """Абстрактный базовый класс для обработчиков уведомлений"""

    @abstractmethod
    async def send(
            self,
            notification: NotificationModel,
            notification_queue: NotificationQueueModel,
            message: str,
            **kwargs
    ) -> bool:
        """
        Отправляет уведомление

        Args:
            notification: Модель уведомления с настройками
            notification_queue: модель уведомления из БД
            message: Текст сообщения для отправки
            **kwargs: Дополнительные параметры

        Returns:
            bool: True если отправка успешна, False в случае ошибки
        """
        pass

    @abstractmethod
    def validate_config(self, options: Dict[str, Any]) -> bool:
        """
        Проверяет корректность конфигурации уведомления

        Args:
            options: Настройки уведомления

        Returns:
            bool: True если конфигурация валидна
        """
        pass

    def send_sync(self, notification: NotificationModel, message: str, **kwargs) -> bool:
        """
        Синхронная версия отправки уведомления

        Args:
            notification: Модель уведомления с настройками
            message: Текст сообщения для отправки
            **kwargs: Дополнительные параметры

        Returns:
            bool: True если отправка успешна, False в случае ошибки
        """
        import asyncio
        return asyncio.run(self.send(notification, message, **kwargs))
