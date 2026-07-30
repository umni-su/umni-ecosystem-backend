# Copyright (C) 2026 Mikhail Sazanov
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from typing import Type, List, Dict, Any
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from classes.notifications.notification_factory import NotificationFactory
from classes.notifications.base_registered_notification import BaseRegisteredNotification


class NotificationPluginHelper:
    """
    Хелпер для плагинов, упрощающий регистрацию и управление уведомлениями
    """

    _plugin_registrations: Dict[str, List[int]] = {}  # plugin_name -> [type_ids]

    @classmethod
    def register_notifications(
            cls,
            plugin_name: str,
            notification_classes: List[Type[BaseRegisteredNotification]]
    ) -> Dict[str, Any]:
        """
        Регистрирует несколько уведомлений от плагина

        Args:
            plugin_name: Имя плагина (для отслеживания)
            notification_classes: Список классов уведомлений

        Returns:
            Dict с результатами регистрации
        """
        results = {
            "success": [],
            "failed": [],
            "errors": {}
        }

        if plugin_name not in cls._plugin_registrations:
            cls._plugin_registrations[plugin_name] = []

        for notification_class in notification_classes:
            try:
                # Пробуем зарегистрировать
                NotificationFactory.register_notification(notification_class)

                # Получаем type_id из экземпляра
                instance = notification_class()
                type_id = instance.type_id

                # Запоминаем, что зарегистрировали от этого плагина
                cls._plugin_registrations[plugin_name].append(type_id)
                results["success"].append(notification_class.__name__)

            except Exception as e:
                error_msg = str(e)
                results["failed"].append(notification_class.__name__)
                results["errors"][notification_class.__name__] = error_msg
                Logger.err(
                    f"Failed to register notification {notification_class.__name__} from plugin {plugin_name}: {e}",
                    LoggerType.NOTIFICATIONS
                )

        Logger.info(
            f"Plugin {plugin_name} registered {len(results['success'])} notifications, "
            f"{len(results['failed'])} failed",
            LoggerType.NOTIFICATIONS
        )

        return results

    @classmethod
    def unregister_plugin_notifications(cls, plugin_name: str) -> Dict[str, Any]:
        """
        Отменяет регистрацию всех уведомлений плагина

        Args:
            plugin_name: Имя плагина

        Returns:
            Dict с результатами отмены регистрации
        """
        results = {
            "success": [],
            "failed": [],
            "errors": {}
        }

        if plugin_name not in cls._plugin_registrations:
            return {
                "message": f"No notifications registered for plugin {plugin_name}",
                "success": [],
                "failed": []
            }

        type_ids = cls._plugin_registrations[plugin_name]

        for type_id in type_ids:
            try:
                if NotificationFactory.unregister_notification(type_id):
                    results["success"].append(type_id)
                else:
                    results["failed"].append(type_id)
                    results["errors"][str(type_id)] = "Unregister failed"
            except Exception as e:
                results["failed"].append(type_id)
                results["errors"][str(type_id)] = str(e)

        # Удаляем запись о плагине
        del cls._plugin_registrations[plugin_name]

        Logger.info(
            f"Plugin {plugin_name} unregistered {len(results['success'])} notifications, "
            f"{len(results['failed'])} failed",
            LoggerType.NOTIFICATIONS
        )

        return results

    @classmethod
    def get_plugin_notifications(cls, plugin_name: str) -> List[int]:
        """Возвращает список ID уведомлений, зарегистрированных плагином"""
        return cls._plugin_registrations.get(plugin_name, [])

    @classmethod
    def get_all_plugin_registrations(cls) -> Dict[str, List[int]]:
        """Возвращает все регистрации плагинов"""
        return cls._plugin_registrations.copy()

    @classmethod
    def clear_all_plugin_registrations(cls) -> int:
        """
        Удаляет все регистрации плагинов (для тестов или очистки)

        Returns:
            int: Количество удаленных уведомлений
        """
        total = 0
        plugin_names = list(cls._plugin_registrations.keys())

        for plugin_name in plugin_names:
            result = cls.unregister_plugin_notifications(plugin_name)
            total += len(result["success"])

        return total
