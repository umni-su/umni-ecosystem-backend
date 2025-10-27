import importlib
import inspect
import os
from typing import Optional, Type

from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from classes.rules.rule_base_executor import RuleBaseExecutor
from models.rule_model import NodeVisualize


class ActionExecutorFactory:
    """Фабрика для динамического создания исполнителей действий из папки actions"""

    # Кэш найденных классов
    _executor_classes_cache = {}

    @classmethod
    def _key_to_class_name(cls, action_key: str) -> str:
        """Преобразование ключа действия в имя класса"""
        parts = action_key.split('.')
        return ''.join(part.capitalize() for part in parts) + 'Executor'

    @classmethod
    def _scan_actions_directory(cls) -> dict:
        """Сканирование папки actions и загрузка классов исполнителей"""
        classes_cache = {}
        actions_dir = os.path.join(os.path.dirname(__file__), 'actions')

        if not os.path.exists(actions_dir):
            Logger.warn(f"Actions directory not found: {actions_dir}", LoggerType.RULES)
            return classes_cache

        # Ищем все Python файлы в папке actions
        for file_name in os.listdir(actions_dir):
            if file_name.endswith('.py') and not file_name.startswith('_'):
                module_name = file_name[:-3]  # Убираем .py

                try:
                    # Импортируем модуль
                    module = importlib.import_module(f'classes.rules.actions.{module_name}')

                    # Ищем классы-исполнители в модуле
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if (issubclass(obj, RuleBaseExecutor) and
                                obj != RuleBaseExecutor and
                                name.endswith('Executor')):

                            # Извлекаем ключ действия из имени класса
                            # Пример: ActionAlarmOnExecutor -> action.alarm.on
                            key_parts = []
                            current_part = []
                            for char in name[:-8]:  # Убираем 'Executor'
                                if char.isupper() and current_part:
                                    key_parts.append(''.join(current_part).lower())
                                    current_part = [char]
                                else:
                                    current_part.append(char)
                            if current_part:
                                key_parts.append(''.join(current_part).lower())

                            action_key = '.'.join(key_parts)
                            classes_cache[action_key] = obj
                            Logger.debug(f"Found executor: {action_key} -> {name}", LoggerType.RULES)

                except ImportError as e:
                    Logger.warn(f"Failed to import module {module_name}: {e}", LoggerType.RULES)

        return classes_cache

    @classmethod
    def _get_executor_class(cls, action_key: str) -> Optional[Type[RuleBaseExecutor]]:
        """Получение класса-исполнителя по ключу действия"""
        # Если кэш пустой - сканируем папку
        if not cls._executor_classes_cache:
            cls._executor_classes_cache = cls._scan_actions_directory()

        # Ищем в кэше
        return cls._executor_classes_cache.get(action_key)

    @classmethod
    def execute_action(cls, node: NodeVisualize) -> bool:
        """Выполнение действия на основе узла - основной метод для вызова из RuleActionExecutor"""
        action_key = node.key

        executor_class = cls._get_executor_class(action_key)

        if executor_class is None:
            Logger.err(f"No executor class found for action: {action_key}", LoggerType.RULES)
            return False

        try:
            Logger.info(f"Executing action: {action_key}", LoggerType.RULES)
            # Создаем экземпляр исполнителя и передаем node
            executor = executor_class(node=node)
            executor.execute()
            return True
        except Exception as e:
            Logger.err(f"Error executing action '{action_key}': {e}", LoggerType.RULES)
            return False

    @classmethod
    def is_action_supported(cls, action_key: str) -> bool:
        """Проверка, поддерживается ли действие"""
        return cls._get_executor_class(action_key) is not None

    @classmethod
    def get_available_actions(cls) -> list:
        """Получение списка доступных действий"""
        if not cls._executor_classes_cache:
            cls._executor_classes_cache = cls._scan_actions_directory()
        return list(cls._executor_classes_cache.keys())
