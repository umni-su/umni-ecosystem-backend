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

from abc import ABC, abstractmethod
from typing import Dict, Any, Type

from classes.l10n.l10n import _
from classes.ui.ui_form_generator import UIEnhancedModel
from models.notification_model import NotificationOptionsBaseModel, NotificationModel
from models.notification_queue_model import NotificationQueueModel


class BaseRegisteredNotification(ABC):
    """Базовый класс для регистрируемых уведомлений"""

    # Обязательные атрибуты для переопределения
    type_id: int = None  # Уникальный числовой идентификатор
    name: str = None  # Уникальное строковое имя
    description: str = ""  # Описание уведомления

    # Модель опций (должна быть унаследована от NotificationOptionsBaseModel)
    options_model: Type[NotificationOptionsBaseModel] = None

    def __init__(self):
        if self.type_id is None:
            raise ValueError(f"Notification {self.__class__.__name__} must define type_id")
        if self.name is None:
            raise ValueError(f"Notification {self.__class__.__name__} must define name")
        if self.options_model is None:
            raise ValueError(f"Notification {self.__class__.__name__} must define options_model")

    @abstractmethod
    async def send(
            self,
            notification: 'NotificationModel',
            notification_queue: 'NotificationQueueModel',
            **kwargs
    ) -> bool:
        """
        Отправляет уведомление

        Args:
            notification: Модель уведомления с настройками
            notification_queue: Модель уведомления из очереди
            **kwargs: Дополнительные параметры

        Returns:
            bool: True если отправка успешна
        """
        pass

    def validate_config(self, options: Dict[str, Any]) -> bool:
        """
        Проверяет корректность конфигурации уведомления

        Args:
            options: Настройки уведомления в виде словаря

        Returns:
            bool: True если конфигурация валидна
        """
        try:
            # Пытаемся создать модель опций
            self.options_model(**options)
            return True
        except Exception as e:
            # Здесь можно добавить логирование если нужно
            return False

    # def get_options_model_instance(self, data: Dict[str, Any]) -> NotificationOptionsBaseModel:
    #     """Создает экземпляр модели опций из данных"""
    #     return self.options_model(**data)

    # def get_ui_schema(self) -> Dict[str, Any]:
    #     """
    #     Возвращает UI схему для модели опций
    #     Исправлено: используем model_json_schema() вместо создания экземпляра
    #     """
    #     if not self.options_model:
    #         return {}
    #
    #     try:
    #         # Получаем JSON схему модели напрямую, без создания экземпляра
    #         schema = self.options_model.model_json_schema()
    #
    #         # Добавляем метаданные из модели
    #         if hasattr(self.options_model, 'model_description'):
    #             schema['model_description'] = _(self.options_model.model_description)
    #         # Добавляем метаданные уведомления
    #         schema['notification_type_id'] = self.type_id
    #         schema['notification_name'] = self.name
    #         schema['notification_description'] = _(self.description)
    #
    #         # Добавляем информацию о чувствительных полях из json_schema_extra
    #         sensitive_fields = []
    #         if hasattr(self.options_model, 'model_fields'):
    #             for field_name, field in self.options_model.model_fields.items():
    #                 if field.json_schema_extra and field.json_schema_extra.get('sensitive'):
    #                     sensitive_fields.append(field_name)
    #                 if field_name in schema.get('properties', {}):
    #                     field_schema = schema['properties'][field_name]
    #
    #                     # Переводим title
    #                     if 'title' in field_schema:
    #                         field_schema['title'] = _(field_schema['title'])
    #
    #                     # Переводим description
    #                     if 'description' in field_schema:
    #                         field_schema['description'] = _(field_schema['description'])
    #
    #         if sensitive_fields:
    #             schema['sensitive_fields'] = sensitive_fields
    #
    #         return schema
    #
    #     except Exception as e:
    #         # В случае ошибки возвращаем базовую структуру
    #         return {
    #             'type': 'object',
    #             'properties': {},
    #             'notification_type_id': self.type_id,
    #             'notification_name': self.name,
    #             'notification_description': _(self.description),
    #             'error': str(e)
    #         }

    def get_ui_schema(self) -> Dict[str, Any]:
        """
        Возвращает UI схему для модели опций, НЕ создавая экземпляр модели.
        """
        if not self.options_model:
            return {}

        try:
            # 1. Получаем "сырую" JSON-схему от КЛАССА модели
            raw_schema = self.options_model.model_json_schema()

            # 2. Строим UI-схему, используя логику из UIEnhancedModel.
            #    Мы не можем вызвать instance.get_ui_schema(), поэтому дублируем или
            #    вызываем вспомогательные методы класса UIEnhancedModel,
            #    передавая им raw_schema и информацию о полях из options_model.
            #    Это safer и не требует создания экземпляра.

            ui_schema = {
                "model_name": self.options_model.__name__,
                # model_uuid можно получить, если он есть как classvar
                "model_uuid": getattr(self.options_model, 'model_uuid', None),
                "model_description": _(getattr(self.options_model, 'model_description', '')),
                "fields": {},
                # Добавляем метаданные уведомления
                "notification_type_id": self.type_id,
                "notification_name": self.name,
                "notification_description": _(self.description),
            }

            # Проходим по полям модели и строим UI-описание для каждого
            if hasattr(self.options_model, 'model_fields'):
                for field_name, field_info in self.options_model.model_fields.items():
                    field_schema = raw_schema["properties"][field_name]

                    # Используем статические методы из UIEnhancedModel для анализа
                    # ВАЖНО: Вам нужно сделать эти методы классами или вынести в утилиты,
                    #        либо вызвать их через класс UIEnhancedModel, если они там объявлены как @classmethod
                    #        Предположим, что UIEnhancedModel._get_ui_type_with_enum - это classmethod

                    # Определяем, чувствительное ли поле
                    extra = field_info.json_schema_extra or {}
                    is_sensitive = extra.get('sensitive', False)
                    sensitive_type = extra.get('sensitive_type', 'encrypted')

                    # Получаем локализованные строки
                    description = field_info.description or ""
                    if description and hasattr(_, '__call__'):
                        description = _(description)

                    label = field_info.title or field_name
                    if hasattr(_, '__call__'):
                        label = _(label)

                    # Собираем поле
                    ui_field = {
                        "type": UIEnhancedModel._get_type_from_json_schema_only(field_schema),  # Если это classmethod
                        "required": field_name in raw_schema.get("required", []),
                        "ui_type": UIEnhancedModel._get_ui_type_with_enum(field_schema, field_info, is_sensitive),
                        # Если это classmethod
                        "label": label,
                        "description": description,
                        "constraints": UIEnhancedModel._get_field_constraints_with_enum(field_schema, field_info),
                        # Если это classmethod
                        "is_sensitive": is_sensitive,
                    }
                    if is_sensitive:
                        ui_field["sensitive_type"] = sensitive_type

                    ui_schema["fields"][field_name] = ui_field

            return ui_schema

        except Exception as e:
            return {
                'error': str(e),
                'notification_type_id': self.type_id,
                'notification_name': self.name,
                'notification_description': _(self.description)
            }

    def get_options_model_instance(self, data: Dict[str, Any]) -> NotificationOptionsBaseModel:
        """Создает экземпляр модели опций из данных"""
        return self.options_model(**data)

    def get_info(self) -> Dict[str, Any]:
        """Возвращает информацию о типе уведомления"""
        return {
            'type_id': self.type_id,
            'name': self.name,
            'description': _(self.description),  # Локализуем здесь
            'options_schema': self.get_ui_schema()
        }
