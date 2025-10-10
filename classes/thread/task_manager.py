import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import cpu_count
from typing import Callable, Optional

from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType


class TaskManager:
    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or (cpu_count() * 2)  # Для I/O-bound можно больше
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.futures = {}  # task_id -> Future
        self.lock = threading.Lock()
        self.is_running = True

        Logger.debug(f"ThreadPool TaskManager started with {self.max_workers} workers", LoggerType.TASKS)

    def submit(self, func: Callable, *args,
               callback: Callable = None, **kwargs) -> str:
        """Добавление задачи в пул потоков"""
        task_id = str(uuid.uuid4())

        def task_wrapper():
            try:
                result = func(*args, **kwargs)
                if callback:
                    callback(task_id, result, None)
                return result
            except Exception as error:
                Logger.debug(f"Task {task_id} failed: {error}", LoggerType.TASKS)
                if callback:
                    callback(task_id, None, str(error))
                raise

        future = self.executor.submit(task_wrapper)

        with self.lock:
            self.futures[task_id] = future

        Logger.debug(f"Task {task_id} submitted", LoggerType.TASKS)
        return task_id

    def get_result(self, task_id: str, timeout: Optional[float] = None):
        """Получить результат задачи (блокирующий)"""
        with self.lock:
            future = self.futures.get(task_id)

        if future:
            return future.result(timeout)
        return None

    def stop(self):
        """Остановка пула потоков"""
        self.is_running = False
        self.executor.shutdown(wait=True)
        Logger.debug("ThreadPool TaskManager stopped", LoggerType.TASKS)

    def __del__(self):
        if self.is_running:
            self.stop()
