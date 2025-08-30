from typing import Callable, Dict, List
import logging
from concurrent.futures import ThreadPoolExecutor
import asyncio

logger = logging.getLogger(__name__)


class EventBus:
    def __init__(self, max_workers: int = 10):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def subscribe(self, event_type: str, callback: Callable):
        """Подписка на событие"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []

        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)
            logger.info(f"Subscribed to {event_type}")

    def unsubscribe(self, event_type: str, callback: Callable):
        """Отписка от события"""
        if event_type in self._subscribers and callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)
            logger.info(f"Unsubscribed from {event_type}")

    async def publish_async(self, event_type: str, *args, **kwargs):
        """Асинхронная публикация события (для использования в FastAPI)"""
        if event_type not in self._subscribers:
            return

        loop = asyncio.get_event_loop()
        tasks = []

        for callback in self._subscribers[event_type]:
            task = loop.run_in_executor(
                self._executor,
                self._execute_callback,
                callback, *args, **kwargs
            )
            tasks.append(task)

        await asyncio.gather(*tasks)

    def _execute_callback(self, callback: Callable, *args, **kwargs):
        """Выполнение callback в отдельном потоке"""
        try:
            callback(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in event handler {callback.__name__}: {e}")

    def get_subscribers_count(self, event_type: str) -> int:
        """Количество подписчиков на событие"""
        return len(self._subscribers.get(event_type, []))


# Глобальный экземпляр шины событий
event_bus = EventBus(max_workers=20)
