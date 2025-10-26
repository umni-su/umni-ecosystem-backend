# notification_queue_service.py
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

import time
from datetime import datetime
from typing import Optional, List
from threading import Lock

from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from models.notification_queue_model import NotificationQueueCreateModel, NotificationQueueModel
from services.base_service import BaseService
from classes.notifications.notification_service import NotificationService
from repositories.notification_queue_repository import NotificationQueueRepository


class NotificationQueueService(BaseService):
    """Сервис для обработки очереди уведомлений"""

    name = "notifications_queue"
    _lock = Lock()
    _processing_interval = 10  # секунды между проверками
    _batch_size = 10  # количество сообщений за одну итерацию

    def run(self):
        while self.running:
            try:
                with self._lock:
                    self._process_queue_batch()

                time.sleep(self._processing_interval)

            except Exception as e:
                Logger.err(f"🔊 Error in main loop {self.name}: {e}", LoggerType.NOTIFICATIONS)
                time.sleep(30)  # пауза при критической ошибке

    def _process_queue_batch(self):
        """Обработка батча сообщений из очереди"""
        try:
            # Получаем сообщения для обработки через репозиторий
            queue_items = NotificationQueueRepository.get_items_for_processing(
                batch_size=self._batch_size
            )

            if not queue_items:
                return

            Logger.info(f"🔊 Process {len(queue_items)} messages in queue", LoggerType.NOTIFICATIONS)

            for queue_item in queue_items:
                self._process_single_message(queue_item)

        except Exception as e:
            Logger.err(f"🔊 Error on batch: {e}")

    def _process_single_message(self, queue_item: NotificationQueueModel):
        """Обработка одного сообщения из очереди"""
        try:
            queue_item.retry_count += 1
            queue_item.last_attempt = datetime.now()
            # Обновляем время последней попытки и счетчик попыток
            success = NotificationQueueRepository.update_queue_item(queue_item)

            if not success:
                Logger.err(f"🔊 Could not update item in queue {queue_item.id}", LoggerType.NOTIFICATIONS)
                return

            # Отправляем уведомление
            success = self._send_notification_sync(queue_item)

            if success:
                # Удаляем успешное сообщение из очереди
                delete_success = NotificationQueueRepository.delete_queue_item(queue_item.id)
                if delete_success:
                    Logger.info(f"🔊 Notification {queue_item.id} success sent and deleted", LoggerType.NOTIFICATIONS)
                else:
                    Logger.err(f"🔊 Notification {queue_item.id} sent, but not deleted", LoggerType.NOTIFICATIONS)
            else:
                Logger.warn(
                    f"🔊 Could not sent notification {queue_item.id}, retry {queue_item.retry_count + 1}",
                    LoggerType.NOTIFICATIONS)

        except Exception as e:
            Logger.err(f"🔊 Error while process message {queue_item.id}: {e}", LoggerType.NOTIFICATIONS)

    def _send_notification_sync(self, queue_item: NotificationQueueModel) -> bool:
        """Синхронная отправка уведомления"""
        try:
            # Импортируем здесь, чтобы избежать циклических импортов
            import asyncio

            # Запускаем асинхронную функцию в синхронном контексте
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                success = loop.run_until_complete(
                    NotificationService.send_notification(
                        notification_queue=queue_item
                    )
                )
                return success
            finally:
                loop.close()

        except Exception as e:
            Logger.err(f"🔊 Error while send notification {queue_item.id}: {e}", LoggerType.NOTIFICATIONS)
            return False

    def add_to_queue(
            self,
            create_model: NotificationQueueCreateModel,
    ) -> bool:
        """Добавление сообщения в очередь"""
        try:
            queue_item = NotificationQueueRepository.create_queue_item(create_model)

            if queue_item:
                Logger.info(
                    f"🔊 Message has been added to the notification queue {queue_item.notification_id} (ID: {queue_item.id})",
                    LoggerType.NOTIFICATIONS)
                return True
            else:
                Logger.err(f"🔊 Couldn't add a message to the notification queue {queue_item}",
                           LoggerType.NOTIFICATIONS)
                return False

        except Exception as e:
            Logger.err(f"🔊 Error when adding to the queue: {e}", LoggerType.NOTIFICATIONS)
            return False

    def retry_failed_messages(self, notification_id: Optional[int] = None) -> int:
        """Повторная обработка неудачных сообщений"""
        try:
            reset_count = NotificationQueueRepository.reset_retry_count(
                notification_id=notification_id
            )

            Logger.info(f"🔊 Dropped attempts for {reset_count} messages", LoggerType.NOTIFICATIONS)
            return reset_count

        except Exception as e:
            Logger.err(f"🔊 Error when resetting attempts: {e}")
            return 0

    def get_queue_stats(self) -> dict:
        """Получение статистики очереди"""
        try:
            return NotificationQueueRepository.get_queue_stats()
        except Exception as e:
            Logger.err(f"🔊 Error when getting statistics: {e}", LoggerType.NOTIFICATIONS)
            return {}

    def cleanup_old_messages(self, days: int = 30) -> int:
        """Очистка старых сообщений из очереди"""
        try:
            deleted_count = NotificationQueueRepository.cleanup_old_items(days=days)
            Logger.info(f"🔊 Deleted {deleted_count} old messages from queue", LoggerType.NOTIFICATIONS)
            return deleted_count

        except Exception as e:
            Logger.err(f"🔊 Error clearing the queue: {e}", LoggerType.NOTIFICATIONS)
            return 0

    def get_pending_messages(self, notification_id: Optional[int] = None) -> List:
        """Получение сообщений, ожидающих обработки"""
        try:
            return NotificationQueueRepository.get_queue_items(
                notification_id=notification_id,
                pending_only=True
            )
        except Exception as e:
            Logger.err(f"🔊 Error when receiving pending messages: {e}", LoggerType.NOTIFICATIONS)
            return []

    def get_failed_messages(self, notification_id: Optional[int] = None) -> List:
        """Получение неудачных сообщений"""
        try:
            all_items = NotificationQueueRepository.get_queue_items(
                notification_id=notification_id
            )
            return [item for item in all_items if item.retry_count >= item.max_retries]
        except Exception as e:
            Logger.err(f"🔊 Error when receiving unsuccessful messages: {e}")
            return []
