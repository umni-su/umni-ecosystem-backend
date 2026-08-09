from typing import Any, Dict, List, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from classes.l10n.l10n import _, ui


class ValidationErrorHandler:
    """
    Класс для обработки ошибок валидации FastAPI/Pydantic с локализацией
    """

    # Маппинг типов ошибок на ключи для gettext
    ERROR_TYPE_MAP = {
        'string_type': 'validation.string_type',
        'missing': 'validation.missing',
        'greater_than': 'validation.greater_than',
        'less_than': 'validation.less_than',
        'int_parsing': 'validation.int_parsing',
        'float_parsing': 'validation.float_parsing',
        'email': 'validation.email',
        'value_error': 'validation.value_error',
        'url_scheme': 'validation.url_scheme',
        'min_length': 'validation.min_length',
        'max_length': 'validation.max_length',
        'pattern': 'validation.pattern',
        'equal_to': 'validation.equal_to',
        'not_equal_to': 'validation.not_equal_to',
        'enum': 'validation.enum',
        'multiple_of': 'validation.multiple_of',
        'decimal_places': 'validation.decimal_places',
    }

    @classmethod
    def get_field_path(cls, loc: List) -> str:
        """
        Извлекает путь к полю из location ошибки
        Пример: ['body', 'account', 'lastname'] -> 'account.lastname'
        """
        # Пропускаем 'body' если он есть
        field_parts = []
        for part in loc:
            # Пропускаем 'body' и числовые индексы (для списков)
            if part != 'body' and not isinstance(part, int):
                field_parts.append(str(part))

        # Если есть числовые индексы, добавляем их в конец
        for part in loc:
            if isinstance(part, int):
                field_parts.append(str(part))

        return '.'.join(field_parts) if field_parts else 'unknown'

    @classmethod
    def translate_error(cls, error: Dict[str, Any]) -> str:
        """
        Перевести сообщение об ошибке используя gettext
        """
        error_type = error.get('type', '')
        ctx = error.get('ctx', {})
        field_path = cls.get_field_path(error.get('loc', []))

        # Получаем оригинальное сообщение как запасной вариант
        original_msg = error.get('msg', 'Validation error')

        # 1. Пробуем получить специфичный для поля перевод
        field_specific_key = f'validation.field.{field_path}.{error_type}'
        translated = ui(field_specific_key)

        # Проверяем, найден ли перевод
        if translated == field_specific_key:
            # 2. Пробуем общий перевод для типа ошибки
            general_key = cls.ERROR_TYPE_MAP.get(error_type, 'validation.default')
            translated = ui(general_key)

            # Если и общий не найден
            if translated == general_key:
                # 3. Используем оригинальное сообщение
                translated = original_msg

        # Подставляем контекстные значения (если есть)
        if ctx and translated and '{' in translated:
            try:
                translated = translated.format(**ctx)
            except (KeyError, ValueError):
                # Если подстановка не удалась, оставляем как есть
                pass

        return translated

    @classmethod
    def format_error(cls, error: Dict[str, Any]) -> Dict[str, Any]:
        """Форматировать одну ошибку для ответа"""
        field_path = cls.get_field_path(error.get('loc', []))

        return {
            "field": field_path,
            "message": cls.translate_error(error),
            "type": error.get('type', 'unknown'),
            "input": error.get('input'),
        }

    @classmethod
    def handle(cls, request: Request, exc: RequestValidationError) -> JSONResponse:
        """Основной метод обработки ошибок валидации"""
        formatted_errors = [cls.format_error(error) for error in exc.errors()]

        # Получаем сообщение об ошибке
        error_message = _('validation.validation_error')
        if error_message == 'validation.validation_error':
            error_message = 'Ошибка валидации данных'

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "status": "error",
                "message": error_message,
                "errors": formatted_errors
            }
        )


# Создаем экземпляр-синглтон
validation_error_handler = ValidationErrorHandler()
