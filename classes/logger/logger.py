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
import os
from datetime import datetime

import uvicorn.logging as u_logging
import logging
import logging.handlers
from typing import Set, Optional, Union, Dict

from classes.logger.logger_types import LoggerType
from config.settings import settings
from models.log_model import LogEntityCode

FILE_FORMAT: str = "%(levelname)s %(asctime)s [%(threadName)s] [%(name)s] [%(loggertype)s] %(message)s"
FORMAT: str = "%(levelprefix)s %(asctime)s [%(threadName)s] [%(name)s] [%(loggertype)s] %(message)s"
DEBUG_MODE = settings.DEBUG_MODE.lower()
DEBUG_MODULES = set(module.strip() for module in DEBUG_MODE.split(',') if module.strip())
LOG_LEVEL = settings.LOG_LEVEL.upper()
LOG_DIR = settings.LOG_DIR

if not os.path.exists(LOG_DIR):
    try:
        os.makedirs(os.path.abspath(LOG_DIR))
    except Exception as e:
        print(e)


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

formatter = CustomFormatter(FORMAT, datefmt="%Y-%m-%d %H:%M:%S")
file_formatter = logging.Formatter(FILE_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")

file_handler = logging.handlers.RotatingFileHandler(
    f"{LOG_DIR}/ecosystem.log",
    maxBytes=100 * 1024 * 1024,  # 100MB
    backupCount=10,
    encoding='utf-8'
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(file_formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)


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
    def _prepare_for_db(
            msg: str,
            level: str,
            logger_type: Optional[LoggerType] = None,
            entity_code: int | None = None
    ) -> Dict:
        """Подготовка данных для БД"""
        return {
            'timestamp': datetime.now(),
            'level': level.upper(),
            'logger_type': logger_type if logger_type else 'GLOBAL',
            'message': msg,
            'entity_id': entity_code.id if isinstance(entity_code, LogEntityCode) else None,
            'code': entity_code.code.value if isinstance(entity_code, LogEntityCode) else None,
        }

    @staticmethod
    def _log_with_type(
            level: str,
            msg: str,
            logger_type: Optional[LoggerType] = None,
            with_db: bool = False,
            entity_code: LogEntityCode | None = None
    ):
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

            if with_db:
                try:
                    # Импортируем только когда нужно
                    from classes.ecosystem import ecosystem

                    # Используем новый метод ecosystem
                    logger_service = ecosystem.get_logger_service()
                    if logger_service:
                        log_data = Logger._prepare_for_db(
                            msg=msg,
                            level=level,
                            logger_type=logger_type.value.upper() if logger_type else 'GLOBAL',
                            entity_code=entity_code
                        )
                        logger_service.add_log(log_data=log_data)
                except Exception as e:
                    # Молча игнорируем ошибки БД логирования
                    print(e)
                    pass

    @staticmethod
    def info(
            msg: str,
            logger_type: Optional[LoggerType] = None,
            with_db: bool = False,
            entity_code: LogEntityCode | None = None
    ):
        Logger._log_with_type('info', msg, logger_type, with_db=with_db, entity_code=entity_code)

    @staticmethod
    def warn(
            msg: str,
            logger_type: Optional[LoggerType] = None,
            with_db: bool = False,
            entity_code: LogEntityCode | None = None
    ):
        Logger._log_with_type('warning', msg, logger_type, with_db=with_db, entity_code=entity_code)

    @staticmethod
    def err(
            msg: str,
            logger_type: Optional[LoggerType] = None,
            with_db: bool = False,
            entity_code: LogEntityCode | None = None
    ):
        Logger._log_with_type('error', str(msg), logger_type, with_db=with_db, entity_code=entity_code)

    @staticmethod
    def debug(
            msg: str,
            logger_type: Optional[LoggerType] = None,
            with_db: bool = False,
            entity_code: LogEntityCode | None = None
    ):
        Logger._log_with_type('debug', msg, logger_type, with_db=with_db, entity_code=entity_code)

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
