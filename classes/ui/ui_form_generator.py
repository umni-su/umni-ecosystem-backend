# Copyright (C) 2025 Mikhail Sazanov
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

import uuid
from enum import Enum

from pydantic import BaseModel
from typing import Any, Dict, List, Optional, get_origin, get_args, ClassVar

from classes.l10n.l10n import _


class UIFieldConfig(BaseModel):
    widget: str
    placeholder: str = ""
    options: List[Any] = []
    step: float = 1


class UIEnhancedModel(BaseModel):
    # Классовые переменные для метаданных модели
    model_uuid: ClassVar[str] = None
    model_description: ClassVar[str] = None

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, 'model_uuid') or cls.model_uuid is None:
            cls.model_uuid = str(uuid.uuid4())

    def get_ui_schema(self) -> Dict[str, Any]:
        schema = self.model_json_schema()
        ui_schema = {
            "model_name": self.__class__.__name__,
            "model_uuid": self.__class__.model_uuid,
            "model_description": _(self.__class__.model_description),
            "fields": {}
        }

        for field_name, field_info in self.model_fields.items():
            field_schema = schema["properties"][field_name]

            # Определяем тип ТОЛЬКО из JSON schema
            field_type = self._get_type_from_json_schema_only(field_schema)

            # Получаем метаданные из json_schema_extra
            extra = field_info.json_schema_extra or {}
            is_sensitive = extra.get('sensitive', False)
            sensitive_type = extra.get('sensitive_type', 'encrypted')

            description = field_info.description or ""
            if description and hasattr(_, '__call__'):
                description = _(description)

            label = field_info.title or field_name
            if hasattr(_, '__call__'):
                label = _(label)

            ui_field = {
                "type": field_type,
                "required": field_name in schema.get("required", []),
                "ui_type": self.__class__._get_ui_type_with_enum(field_schema, field_info, is_sensitive),
                "label": label,
                "description": description,
                "constraints": self.__class__._get_field_constraints_with_enum(field_schema, field_info),
                "is_sensitive": is_sensitive,
                "sensitive_type": sensitive_type if is_sensitive else None,
                "value": getattr(self, field_name)  # вот эта строчка
            }
            ui_schema["fields"][field_name] = ui_field

        return ui_schema

    @classmethod
    def _get_type_from_json_schema_only(cls, field_schema: Dict) -> str:
        """Получаем тип только из JSON schema"""
        # Для anyOf полей (Optional)
        if "anyOf" in field_schema:
            for item in field_schema["anyOf"]:
                if "type" in item and item["type"] != "null":
                    return item["type"]
                elif "$ref" in item:
                    # Для ссылок возвращаем string (enum всегда string)
                    return "string"

        # Для обычных полей
        if "type" in field_schema:
            return field_schema["type"]

        return "string"

    @classmethod
    def _get_localized_label(cls, label: str) -> str:
        """Локализует метку поля если доступна функция _"""
        if hasattr(_, '__call__'):
            try:
                return _(label)
            except:
                return label
        return label

    @classmethod
    def _get_field_type(cls, field_info) -> str:
        """Получаем основной тип поля, учитывая Optional"""
        annotation = field_info.annotation

        # Если поле Optional, извлекаем внутренний тип
        if get_origin(annotation) is Optional:
            args = get_args(annotation)
            if args:
                main_type = args[0]
                return cls._type_to_string(main_type)

        return cls._type_to_string(annotation)

    @classmethod
    def _type_to_string(cls, type_obj) -> str:
        """Конвертируем тип в строку"""
        # Если это класс Enum, возвращаем "string"
        if isinstance(type_obj, type) and issubclass(type_obj, Enum):
            return "string"

        # Базовые типы
        if type_obj is str:
            return "string"
        elif type_obj is int:
            return "integer"
        elif type_obj is float:
            return "number"
        elif type_obj is bool:
            return "boolean"
        else:
            # Для неизвестных типов пытаемся получить имя
            return getattr(type_obj, "__name__", "unknown")

    @classmethod
    def _get_ui_type_with_enum(cls, field_schema: Dict, field_info, is_sensitive: bool) -> str:
        """Определяем ui_type с учетом Enum"""
        # Для sensitive полей всегда password
        if is_sensitive:
            return "password"

        # Проверяем Enum через аннотацию
        if cls._is_enum_field(field_info):
            return "select"

        # Проверяем enum в JSON schema (в $defs)
        if "anyOf" in field_schema:
            for item in field_schema["anyOf"]:
                if "$ref" in item and "EncryptionEnum" in item["$ref"]:
                    return "select"

        # Проверяем наличие $ref в JSON schema
        if "$ref" in field_schema and "Enum" in field_schema["$ref"]:
            return "select"

        # Базовые типы
        field_type = cls._get_field_type(field_info)
        type_mapping = {
            "string": "text",
            "integer": "number",
            "number": "number",
            "boolean": "checkbox",
        }

        return type_mapping.get(field_type, "text")

    @classmethod
    def _is_enum_field(cls, field_info) -> bool:
        """Проверяем, является ли поле Enum"""
        try:
            annotation = field_info.annotation

            # Проверяем Optional[Enum]
            if get_origin(annotation) is Optional:
                args = get_args(annotation)
                if args:
                    inner_type = args[0]
                    # Проверяем, является ли внутренний тип Enum
                    return isinstance(inner_type, type) and issubclass(inner_type, Enum)

            # Проверяем просто Enum
            return isinstance(annotation, type) and issubclass(annotation, Enum)
        except (TypeError, AttributeError):
            return False

    @classmethod
    def _get_field_constraints_with_enum(cls, field_schema: Dict, field_info) -> Dict:
        """Получаем constraints с учетом Enum"""
        constraints = {}

        # Базовые constraints
        for key, ui_key in [
            ("minimum", "min"),
            ("maximum", "max"),
            ("minLength", "minLength"),
            ("maxLength", "maxLength"),
            ("pattern", "pattern")
        ]:
            if key in field_schema:
                constraints[ui_key] = field_schema[key]

        # Options для select
        options = []

        # 1. Проверяем Enum через аннотацию (самый надежный способ)
        if cls._is_enum_field(field_info):
            options = cls._get_enum_options_from_class(field_info)

        # 2. Если не получили options из класса, проверяем JSON schema $defs
        if not options and "anyOf" in field_schema:
            for item in field_schema["anyOf"]:
                if "$ref" in item and "EncryptionEnum" in item["$ref"]:
                    # Получаем enum из $defs JSON schema
                    defs_key = item["$ref"].split("/")[-1]
                    if defs_key in cls.model_json_schema().get("$defs", {}):
                        enum_def = cls.model_json_schema()["$defs"][defs_key]
                        if "enum" in enum_def:
                            options = [
                                {"value": opt, "label": cls._get_localized_label(opt)}
                                for opt in enum_def["enum"]
                            ]

        if options:
            constraints["options"] = options

        return constraints

    @classmethod
    def _get_enum_options_from_class(cls, field_info) -> List[Dict]:
        """Получаем options напрямую из Enum класса"""
        try:
            options = []
            annotation = field_info.annotation

            # Извлекаем Enum класс из Optional[Enum]
            enum_class = None
            if get_origin(annotation) is Optional:
                args = get_args(annotation)
                if args and isinstance(args[0], type) and issubclass(args[0], Enum):
                    enum_class = args[0]
            elif isinstance(annotation, type) and issubclass(annotation, Enum):
                enum_class = annotation

            if enum_class:
                print(f"Found enum class: {enum_class}, members: {list(enum_class)}")
                for enum_member in enum_class:
                    options.append({
                        "value": enum_member.value,
                        "label": cls._get_localized_label(enum_member.value) or enum_member.value
                    })

            return options
        except Exception as e:
            print(f"Error in _get_enum_options_from_class: {e}")
            return []
