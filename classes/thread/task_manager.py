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

from multiprocessing import Process, Queue, Lock, cpu_count
from typing import Callable
import queue

from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType


class TaskManager:
    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or cpu_count()
        self.task_queue = Queue()
        self.lock = Lock()
        self.workers = []
        self.is_running = False

    def start(self):
        """Запуск worker процессов"""
        self.is_running = True
        for i in range(self.max_workers):
            worker = Process(
                target=self._worker_loop,
                args=(self.task_queue, self.lock),
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
        Logger.debug(f"Started {self.max_workers} workers", LoggerType.TASKS)

    @staticmethod
    def _worker_loop(task_queue: Queue, lock: Lock):
        """Цикл выполнения задач с полной обработкой ошибок"""
        while True:
            try:
                # Безопасное получение задачи
                task_data = task_queue.get(timeout=1)

                # Проверяем формат задачи
                if not isinstance(task_data, tuple) or len(task_data) != 5:
                    print(f"Invalid task format: {task_data}")
                    continue

                task_id, func, args, kwargs, callback = task_data

                # Выполняем задачу
                try:
                    with lock:
                        result = func(*args, **kwargs)
                        Logger.debug(f"Task {task_id} completed", LoggerType.TASKS)

                    # Успешный callback
                    if callable(callback):
                        callback(task_id, result, None)

                except Exception as task_error:
                    Logger.debug(f"Task {task_id} failed: {task_error}", LoggerType.TASKS)
                    if callable(callback):
                        callback(task_id, None, str(task_error))

            except queue.Empty:
                continue  # Нормальная ситуация - нет задач
            except KeyboardInterrupt:
                break  # Корректный выход
            except Exception as fatal_error:
                Logger.err(f"Fatal worker error: {fatal_error}", LoggerType.TASKS)
                break

    def submit(self, func: Callable, *args,
               callback: Callable = None, **kwargs) -> str:
        """Добавление задачи в очередь"""
        import uuid
        task_id = str(uuid.uuid4())
        self.task_queue.put((task_id, func, args, kwargs, callback))
        Logger.debug(f"Task {task_id} submitted", LoggerType.TASKS)
        return task_id

    def stop(self):
        """Остановка всех worker'ов"""
        self.is_running = False
        for worker in self.workers:
            worker.terminate()
        Logger.err("All workers stopped", LoggerType.TASKS)
