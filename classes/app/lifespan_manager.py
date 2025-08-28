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

import signal
import contextlib
from typing import AsyncIterator, Any
from fastapi import FastAPI

from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from services.cameras.cameras_service import CamerasService
from services.cameras.classes.stream_registry import StreamRegistry, StreamState

from database.migrations import MigrationManager
from classes.ecosystem import Ecosystem
from services.rule.rule_service import RuleService


class LifespanManager:
    _instance = None
    _shutting_down = False
    _original_handlers = {}

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
        self._shutting_down = True
        StreamRegistry.set_state(StreamState.SHUTTING_DOWN)
        self._perform_shutdown()  # added

        # Вызываем оригинальный обработчик (для uvicorn)
        if signum in self._original_handlers and self._original_handlers[signum]:
            self._original_handlers[signum](signum, frame)

    def _perform_shutdown(self):
        """Выполняет фактическое завершение работы"""
        if self._shutting_down:
            return

        self._shutting_down = True
        Logger.debug("Stopping all streams gracefully...", LoggerType.APP)
        StreamRegistry.stop_all_streams()
        for stream in CamerasService.streams:
            stream.opened = False
            stream.destroy_output_container()
            Logger.warn(f'❌ {stream.camera.name} Force stop camera stream', LoggerType.APP)

        RuleService.task_manager.stop()

    @contextlib.asynccontextmanager
    async def lifespan(self, app: FastAPI) -> AsyncIterator[None]:
        """Lifespan handler для FastAPI"""
        # Startup
        MigrationManager.run_migrations()
        ecosystem = Ecosystem()
        Logger.info('Generator lifespan at start of app')
        self._shutting_down = False
        self._setup_signal_handlers()
        StreamRegistry.set_state(StreamState.RUNNING)
        Logger.debug("Application starting up...", LoggerType.APP)

        yield

        # Shutdown
        self._perform_shutdown()
        Logger.debug("Application shutting down...", LoggerType.APP)


# Глобальный экземпляр
lifespan_manager = LifespanManager()
