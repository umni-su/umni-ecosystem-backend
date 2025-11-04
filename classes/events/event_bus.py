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

from typing import Callable, Dict, List, Any
import logging
from concurrent.futures import ThreadPoolExecutor
import threading
import atexit
from functools import wraps

from classes.logger.logger import Logger


class EventBus:
    _instance = None
    _lock = threading.RLock()

    def __new__(cls, max_workers: int = 10):
        """Синглтон паттерн для глобальной шины событий"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialize(max_workers)
            return cls._instance

    def _initialize(self, max_workers: int):
        """Инициализация шины событий"""
        self._subscribers: Dict[str, List[Callable]] = {}
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="event_bus_"
        )
        self._subscribers_lock = threading.RLock()
        self._is_shutdown = False

        # Регистрируем очистку при выходе
        atexit.register(self.shutdown)

    def subscribe(self, event_type: str, callback: Callable) -> None:
        """Подписка на событие с потокобезопасностью"""
        if self._is_shutdown:
            Logger.warn("EventBus is shutdown, cannot subscribe")
            return

        with self._subscribers_lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []

            if callback not in self._subscribers[event_type]:
                self._subscribers[event_type].append(callback)
                Logger.debug(f"✒️ Subscribed to {event_type}, total: {len(self._subscribers[event_type])}")

    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        """Отписка от события с потокобезопасностью"""
        if self._is_shutdown:
            return

        with self._subscribers_lock:
            if event_type in self._subscribers:
                if callback in self._subscribers[event_type]:
                    self._subscribers[event_type].remove(callback)
                    Logger.debug(f"Unsubscribed from {event_type}, remaining: {len(self._subscribers[event_type])}")

                # Удаляем пустой список подписчиков
                if not self._subscribers[event_type]:
                    del self._subscribers[event_type]

    def publish(self, event_type: str, *args, **kwargs) -> None:
        """Публикация события с обработкой в отдельных потоках"""
        if self._is_shutdown:
            Logger.warning("EventBus is shutdown, cannot publish")
            return

        # Получаем копию обработчиков под блокировкой
        callbacks = self._get_callbacks_copy(event_type)

        if not callbacks:
            Logger.debug(f"No subscribers for event: {event_type}")
            return

        # Запускаем каждый обработчик в отдельном потоке
        for callback in callbacks:
            self._executor.submit(
                self._execute_callback_safe,
                callback, event_type, *args, **kwargs
            )

    def publish_sync(self, event_type: str, *args, **kwargs) -> List[Any]:
        """Синхронная публикация события (возвращает результаты)"""
        if self._is_shutdown:
            Logger.warning("EventBus is shutdown, cannot publish")
            return []

        callbacks = self._get_callbacks_copy(event_type)
        results = []

        if not callbacks:
            Logger.debug(f"No subscribers for event: {event_type}")
            return results

        for callback in callbacks:
            try:
                result = callback(*args, **kwargs)
                results.append(result)
            except Exception as e:
                Logger.err(f"Error in sync event handler {callback.__name__} for {event_type}: {e}")
                results.append(None)

        return results

    def _get_callbacks_copy(self, event_type: str) -> List[Callable]:
        """Потокобезопасное получение копии обработчиков"""
        with self._subscribers_lock:
            return self._subscribers.get(event_type, [])[:]  # Возвращаем копию

    def _execute_callback_safe(self, callback: Callable, event_type: str, *args, **kwargs) -> None:
        """Безопасное выполнение callback с обработкой ошибок"""
        try:
            callback(*args, **kwargs)
            # Logger.debug(f"Successfully executed handler {callback.__name__} for {event_type}")
        except Exception as e:
            Logger.err(f"Error in event handler {callback.__name__} for {event_type}: {e}")

    def get_subscribers_count(self, event_type: str) -> int:
        """Количество подписчиков на событие"""
        with self._subscribers_lock:
            return len(self._subscribers.get(event_type, []))

    def get_all_events(self) -> List[str]:
        """Получить список всех зарегистрированных событий"""
        with self._subscribers_lock:
            return list(self._subscribers.keys())

    def clear_event(self, event_type: str) -> None:
        """Очистить все подписки на событие"""
        with self._subscribers_lock:
            if event_type in self._subscribers:
                del self._subscribers[event_type]
                Logger.info(f"Cleared all subscribers for {event_type}")

    def shutdown(self) -> None:
        """Корректное завершение работы шины событий"""
        if self._is_shutdown:
            return

        self._is_shutdown = True
        Logger.info("Shutting down EventBus...")

        # Завершаем executor
        self._executor.shutdown(wait=True)

        # Очищаем подписчиков
        with self._subscribers_lock:
            self._subscribers.clear()

        Logger.info("EventBus shutdown complete")


# Декоратор для удобной подписки
def event_handler(event_type: str):
    """Декоратор для автоматической подписки на события"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # Подписываем функцию на событие
        event_bus.subscribe(event_type, wrapper)
        return wrapper

    return decorator


# Глобальный экземпляр шины событий
event_bus = EventBus(max_workers=20)
