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


from typing import Dict, Optional, List, Any, Type
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from classes.notifications.base_registered_notification import BaseRegisteredNotification
from entities.enums.notification_type_enum import NotificationTypeEnum


class NotificationFactory:
    """Фабрика для создания и управления обработчиками уведомлений"""

    # Основное хранилище зарегистрированных уведомлений
    _notifications: Dict[int, BaseRegisteredNotification] = {}
    _notifications_by_name: Dict[str, BaseRegisteredNotification] = {}

    @classmethod
    def register_notification(cls, notification_class: Type[BaseRegisteredNotification]) -> None:
        """
        Регистрирует новый тип уведомления

        Args:
            notification_class: Класс уведомления (должен быть унаследован от BaseRegisteredNotification)

        Raises:
            ValueError: Если тип с таким ID или именем уже зарегистрирован
        """
        try:
            # Создаем экземпляр для проверки
            notification_instance = notification_class()

            # Проверяем уникальность type_id
            if notification_instance.type_id in cls._notifications:
                raise ValueError(
                    f"Notification type with ID {notification_instance.type_id} "
                    f"already registered: {cls._notifications[notification_instance.type_id].name}"
                )

            # Проверяем уникальность name
            if notification_instance.name in cls._notifications_by_name:
                raise ValueError(
                    f"Notification with name '{notification_instance.name}' "
                    f"already registered (ID: {cls._notifications_by_name[notification_instance.name].type_id})"
                )

            # Регистрируем уведомление
            cls._notifications[notification_instance.type_id] = notification_instance
            cls._notifications_by_name[notification_instance.name] = notification_instance

            Logger.info(
                f"📝 Registered notification: {notification_instance.name} (ID: {notification_instance.type_id})",
                LoggerType.NOTIFICATIONS
            )

        except Exception as e:
            Logger.err(f"Failed to register notification {notification_class.__name__}: {e}", LoggerType.NOTIFICATIONS)
            raise

    @classmethod
    def register_from_enum(cls, enum_value: NotificationTypeEnum,
                           notification_class: Type[BaseRegisteredNotification]) -> None:
        """
        Регистрирует уведомление с использованием существующего enum (для обратной совместимости)

        Args:
            enum_value: Значение enum (должно содержать value и name)
            notification_class: Класс уведомления
        """
        # Временно устанавливаем type_id и name из enum
        notification_class.type_id = enum_value.value
        notification_class.name = enum_value.name.lower()
        cls.register_notification(notification_class)

    @classmethod
    def get_handler(cls, notification_type: int) -> Optional[BaseRegisteredNotification]:
        """
        Возвращает обработчик для указанного типа уведомления по ID

        Args:
            notification_type: ID типа уведомления

        Returns:
            BaseRegisteredNotification или None если не найден
        """
        handler = cls._notifications.get(notification_type)
        if not handler:
            Logger.warn(f"Notification type with ID {notification_type} not found", LoggerType.NOTIFICATIONS)
        return handler

    @classmethod
    def get_handler_by_name(cls, name: str) -> Optional[BaseRegisteredNotification]:
        """
        Возвращает обработчик по имени уведомления

        Args:
            name: Имя уведомления

        Returns:
            BaseRegisteredNotification или None если не найден
        """
        return cls._notifications_by_name.get(name)

    @classmethod
    def get_all_notifications(cls, sort_by='id', reverse=False) -> List[Dict[str, Any]]:
        """
        Возвращает список всех зарегистрированных уведомлений

        Args:
            sort_by: 'id' или 'name'
            reverse: True для обратной сортировки
        """
        notifications = list(cls._notifications.values())

        if sort_by == 'name':
            notifications.sort(key=lambda x: x.name, reverse=reverse)
        else:  # по id по умолчанию
            notifications.sort(key=lambda x: x.type_id, reverse=reverse)

        return [n.get_info() for n in notifications]

    @classmethod
    def get_notification_names(cls) -> List[str]:
        """Возвращает список имен всех зарегистрированных уведомлений"""
        return list(cls._notifications_by_name.keys())

    @classmethod
    def get_notification_ids(cls) -> List[int]:
        """Возвращает список ID всех зарегистрированных уведомлений"""
        return list(cls._notifications.keys())

    @classmethod
    def get_ui_schemas(cls) -> Dict[int, Dict[str, Any]]:
        """
        Возвращает UI схемы для всех зарегистрированных уведомлений

        Returns:
            Dict[int, Dict]: Словарь {type_id: ui_schema}
        """
        return {
            type_id: notification.get_ui_schema()
            for type_id, notification in cls._notifications.items()
        }

    @classmethod
    def validate_notification_config(cls, notification_type: int, options: Dict[str, Any]) -> bool:
        """
        Проверяет корректность конфигурации уведомления

        Args:
            notification_type: ID типа уведомления
            options: Настройки уведомления

        Returns:
            bool: Результат валидации
        """
        handler = cls.get_handler(notification_type)
        if not handler:
            return False
        return handler.validate_config(options)

    @classmethod
    def unregister_notification(cls, notification_type: int) -> bool:
        """
        Удаляет регистрацию уведомления (для плагинов при выгрузке)

        Args:
            notification_type: ID типа уведомления

        Returns:
            bool: True если успешно удалено
        """
        if notification_type in cls._notifications:
            notification = cls._notifications[notification_type]
            del cls._notifications_by_name[notification.name]
            del cls._notifications[notification_type]
            Logger.info(f"📝 Unregistered notification: {notification.name} (ID: {notification_type})",
                        LoggerType.NOTIFICATIONS)
            return True
        return False
