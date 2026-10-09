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

import asyncio
import signal
import contextlib
import threading
import time
from typing import AsyncIterator, Any
from fastapi import FastAPI

from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from classes.websockets.websockets import WebSockets
from classes.notifications.notification_factory import NotificationFactory
from classes.notifications.via.email_notification import EmailNotification
from classes.notifications.via.matrix_notification import MatrixNotification
from classes.notifications.via.telegram_notification import TelegramNotification
from entities.enums.notification_type_enum import NotificationTypeEnum
from services.cameras.cameras_service import CamerasService
from services.cameras.classes.camera_notifier import CameraNotifier
from services.cameras.classes.stream_registry import StreamRegistry, StreamState

from database.migrations import MigrationManager
from classes.ecosystem import Ecosystem
from services.rule.rule_service import RuleService


class LifespanManager:
    _instance = None
    _shutting_down = False
    _shutdown_done = False
    _shutdown_lock = threading.Lock()
    _original_handlers = {}
    shutdown_timeout = 30  # Общий бюджет ожидания остановки потоков камер (сек)

    @property
    def is_shutting_down(self) -> bool:
        return self._shutting_down

    def _setup_signal_handlers(self):
        """Устанавливаем обработчики сигналов"""
        signals = [signal.SIGINT, signal.SIGTERM]

        for sig in signals:
            self._original_handlers[sig] = signal.getsignal(sig)
            signal.signal(sig, self._signal_handler)

    def _signal_handler(self, signum: int, frame: Any):
        """Обработчик сигналов для graceful shutdown"""
        Logger.debug(f"Received signal {signum}, initiating graceful shutdown...", LoggerType.APP)
        # _perform_shutdown идемпотентен и сам выставляет _shutting_down,
        # поэтому здесь его НЕ выставляем заранее (иначе shutdown был бы пропущен)
        self._perform_shutdown()

        # Вызываем оригинальный обработчик (для uvicorn)
        if signum in self._original_handlers and self._original_handlers[signum]:
            self._original_handlers[signum](signum, frame)

    def _perform_shutdown(self):
        """Выполняет фактическое завершение работы (идемпотентно)."""
        with self._shutdown_lock:
            if self._shutdown_done:
                return
            self._shutdown_done = True
            self._shutting_down = True

        Logger.debug("Stopping all streams gracefully...", LoggerType.APP)

        # 0. Останавливаем фоновые сервисы (плагины и т.п.) через их on_stop()
        try:
            Ecosystem().stop_services()
        except Exception as e:
            Logger.err(f"Error stopping services: {e}", LoggerType.APP)

        # 1. Останавливаем опрос камер, чтобы потоки не пересоздавались
        try:
            CamerasService.stop_polling()
        except Exception as e:
            Logger.err(f"Error stopping cameras polling: {e}", LoggerType.APP)

        # 2. Переводим реестр в состояние завершения
        StreamRegistry.set_state(StreamState.SHUTTING_DOWN)

        streams = StreamRegistry.get_all_streams()

        # 3. Сначала быстро сигнализируем всем потокам остановку
        for stream in streams:
            try:
                stream.request_stop()
            except Exception as e:
                Logger.err(f"Error requesting stream stop: {e}", LoggerType.APP)

        # 4. Дожидаемся завершения всех потоков в рамках общего бюджета
        deadline = time.time() + self.shutdown_timeout
        for stream in streams:
            try:
                remaining = max(0.0, deadline - time.time())
                daemon_alive = not stream.join_thread(timeout=remaining)
                stream.finalize_stop(daemon_alive)
                if daemon_alive:
                    Logger.warn(f'❌ {stream.camera.name} stream did not stop in time', LoggerType.APP)
            except Exception as e:
                Logger.err(f"Error stopping stream: {e}", LoggerType.APP)

        # 5. Останавливаем пул правил
        try:
            RuleService.task_manager.stop()
        except Exception as e:
            Logger.err(f"Error stopping rule task manager: {e}", LoggerType.APP)

        # 6. Останавливаем пул нотификаций камер
        try:
            CameraNotifier.shutdown()
        except Exception as e:
            Logger.err(f"Error stopping camera notifier: {e}", LoggerType.APP)

        Logger.debug("Application streams stopped", LoggerType.APP)

    @contextlib.asynccontextmanager
    async def lifespan(self, app: FastAPI) -> AsyncIterator[None]:
        """Lifespan handler для FastAPI"""
        # Startup

        ecosystem = Ecosystem()
        ecosystem.register_non_auto_subscribers()
        ecosystem.start_background_tasks()
        Logger.info('Generator lifespan at start of app')
        # Запоминаем серверный event loop: WebSocket-сообщения из фоновых
        # потоков должны планироваться в нём, а не в новых loop'ах
        WebSockets.set_loop(asyncio.get_running_loop())
        self._shutting_down = False
        self._shutdown_done = False
        CamerasService.start_polling()
        self._setup_signal_handlers()
        StreamRegistry.set_state(StreamState.RUNNING)

        NotificationFactory.register_notification(TelegramNotification)
        NotificationFactory.register_notification(EmailNotification)
        NotificationFactory.register_notification(MatrixNotification)

        Logger.debug("Application starting up...", LoggerType.APP)

        yield

        # Shutdown
        self._perform_shutdown()
        WebSockets.clear_loop()
        Logger.debug("Application shutting down...", LoggerType.APP)


# Глобальный экземпляр
lifespan_manager = LifespanManager()
