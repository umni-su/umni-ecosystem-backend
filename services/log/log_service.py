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

import threading
import queue
import time
from datetime import datetime, timedelta
from typing import List, Dict

from config.settings import settings
from database.session import write_session
from entities.log_entry import LogEntity
from repositories.log_repository import LogRepository
from services.base_service import BaseService
from services.scheduler.classes.task_scheduler import scheduler
from services.scheduler.enums.schedule_frequency import ScheduleFrequency
from services.scheduler.models.task_schedule import TaskSchedule


class LogService(BaseService):
    """Фоновый воркер для асинхронной записи логов в БД"""

    name = 'log'
    queue = queue.Queue(
        maxsize=10000
    )
    buffer = None
    flush_interval = None
    batch_size = None

    @classmethod
    def add_log(cls, log_data: Dict):
        """Добавление лога в очередь (неблокирующее)"""
        try:
            LogService.queue.put_nowait(log_data)
        except queue.Full:
            # При переполнении - пишем в emergency файл
            cls._write_to_emergency_file(log_data)

    def clear_old_logs(self):
        LogRepository.delete_old_logs(1)

    def run(self):

        scheduler.add_task(
            func=self.clear_old_logs,
            schedule_cfg=TaskSchedule(
                frequency=ScheduleFrequency.MINUTE,
                interval=settings.LOG_DB_DELETE_AFTER_DAYS
            ))

        """Основной цикл воркера"""
        last_flush = time.time()

        self.batch_size = settings.LOG_BATCH_SIZE or 50
        self.flush_interval = settings.LOG_FLUSH_INTERVAL or 5
        self.buffer: List[Dict] = []
        self.thread = None

        while self.running:
            try:
                # Неблокирующее чтение из очереди
                try:
                    log_data = LogService.queue.get_nowait()
                    self.buffer.append(log_data)
                except queue.Empty:
                    pass

                # Проверяем условия для flush
                current_time = time.time()
                should_flush = (
                        len(self.buffer) >= self.batch_size or
                        int(current_time - last_flush) >= self.flush_interval
                )

                if should_flush and self.buffer:
                    self._flush_buffer()
                    last_flush = current_time

                time.sleep(0.01)  # Не грузим CPU

            except Exception as e:
                self._handle_error(e)

    def _flush_buffer(self):
        """Пакетная запись в БД"""
        if not self.buffer:
            return

        try:
            with write_session() as session:
                # Bulk insert
                session.bulk_insert_mappings(LogEntity, self.buffer)
                session.commit()
                # print('Flushing', self.buffer)
                pass

            # Очистка только после успешного commit
            self.buffer.clear()

        except Exception as e:
            # При ошибке БД - пишем в файл для последующей синхронизации
            self.buffer.clear()

    @classmethod
    def _write_to_emergency_file(cls, log_data: Dict):
        """Запись в emergency файл при переполнении очереди"""
        # with open('/tmp/logs_emergency.ndjson', 'a') as f:
        #    f.write(json.dumps(log_data) + '\n')
        print(str(log_data))

    @classmethod
    def _handle_error(cls, error: Exception):
        """Обработка ошибок воркера"""
        # with open('/tmp/log_worker_errors.log', 'a') as f:
        #    f.write(f"{time.time()}: {str(error)}\n")
        print(error)
