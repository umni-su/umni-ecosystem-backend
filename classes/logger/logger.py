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

import uvicorn.logging as u_logging
import logging
from typing import Set, Optional, Union

from classes.logger.logger_types import LoggerType
from config.settings import settings

FORMAT: str = "%(levelprefix)s %(asctime)s [%(threadName)s] [%(name)s] [%(loggertype)s] %(message)s"

# Чтение настроек из environment variables
DEBUG_MODE = settings.DEBUG_MODE.lower()
DEBUG_MODULES = set(module.strip() for module in DEBUG_MODE.split(',') if module.strip())
LOG_LEVEL = settings.LOG_LEVEL.upper()


# Кастомный форматтер для добавления типа лога
class CustomFormatter(u_logging.DefaultFormatter):
    def format(self, record):
        # Добавляем поле loggertype в запись
        if not hasattr(record, 'loggertype'):
            record.loggertype = 'GLOBAL'
        return super().format(record)


# Настройка основного логгера
logger = logging.getLogger("logger")

# Установка уровня логирования
try:
    log_level = getattr(logging, LOG_LEVEL)
    logger.setLevel(log_level)
except AttributeError:
    logger.setLevel(logging.INFO)
    logger.warning(f"Invalid LOG_LEVEL '{LOG_LEVEL}', defaulting to INFO")

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = CustomFormatter(FORMAT, datefmt="%Y-%m-%d %H:%M:%S")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


class Logger:
    # Экспорт перечисления для удобного использования
    Type = LoggerType

    @staticmethod
    def _should_log(logger_type: Optional[LoggerType] = None) -> bool:
        """Проверяет, нужно ли логировать сообщение для данного типа логгера"""
        if not logger_type:
            return True  # Сообщения без типа всегда логируются

        if not DEBUG_MODULES:
            return False  # Если DEBUG_MODE не задан, типизированные сообщения не логируются

        if logger_type == LoggerType.ALL:
            return bool(DEBUG_MODULES)  # ALL логируется, если есть любой модуль

        return logger_type.value in DEBUG_MODULES

    @staticmethod
    def _log_with_type(level: str, msg: str, logger_type: Optional[LoggerType] = None):
        """Вспомогательный метод для логирования с типом"""
        if Logger._should_log(logger_type):
            # Создаем extra dict с информацией о типе
            extra = {'loggertype': logger_type.value.upper() if logger_type else 'GLOBAL'}

            # Логируем с дополнительными полями
            if level == 'info':
                logger.info(msg, extra=extra)
            elif level == 'warning':
                logger.warning(msg, extra=extra)
            elif level == 'error':
                logger.error(msg, extra=extra)
            elif level == 'debug':
                logger.debug(msg, extra=extra)

    @staticmethod
    def info(msg: str, logger_type: Optional[LoggerType] = None):
        Logger._log_with_type('info', msg, logger_type)

    @staticmethod
    def warn(msg: str, logger_type: Optional[LoggerType] = None):
        Logger._log_with_type('warning', msg, logger_type)

    @staticmethod
    def err(msg: Union[str, Exception], logger_type: Optional[LoggerType] = None):
        Logger._log_with_type('error', str(msg), logger_type)

    @staticmethod
    def debug(msg: str, logger_type: Optional[LoggerType] = None):
        Logger._log_with_type('debug', msg, logger_type)

    @staticmethod
    def set_level(level: str):
        """Динамически изменяет уровень логирования"""
        try:
            log_level = getattr(logging, level.upper())
            logger.setLevel(log_level)
            logger.info(f"Log level changed to {level.upper()}")
        except AttributeError:
            logger.warning(f"Invalid log level: {level}")

    @staticmethod
    def get_current_level() -> str:
        """Возвращает текущий уровень логирования"""
        return logging.getLevelName(logger.level)

    @staticmethod
    def get_debug_modules() -> Set[str]:
        """Возвращает текущие активные модули отладки"""
        return DEBUG_MODULES.copy()

    @staticmethod
    def add_debug_module(module: str):
        """Добавляет модуль в DEBUG_MODULES"""
        DEBUG_MODULES.add(module.lower())

    @staticmethod
    def remove_debug_module(module: str):
        """Удаляет модуль из DEBUG_MODULES"""
        DEBUG_MODULES.discard(module.lower())

    @staticmethod
    def is_module_enabled(module: Union[str, LoggerType]) -> bool:
        """Проверяет, включен ли модуль для отладки"""
        if isinstance(module, LoggerType):
            module = module.value
        return module.lower() in DEBUG_MODULES
