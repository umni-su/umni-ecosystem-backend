import signal
import contextlib
from typing import AsyncIterator, Any
from fastapi import FastAPI

from classes.logger import Logger
from services.cameras.cameras_service import CamerasService
from services.cameras.classes.stream_registry import StreamRegistry, StreamState

from database.migrations import MigrationManager
from classes.ecosystem import Ecosystem


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
        print(f"Received signal {signum}, initiating graceful shutdown...")
        self._shutting_down = True
        StreamRegistry.set_state(StreamState.SHUTTING_DOWN)

        # Вызываем оригинальный обработчик (для uvicorn)
        if signum in self._original_handlers and self._original_handlers[signum]:
            self._original_handlers[signum](signum, frame)

    def _perform_shutdown(self):
        """Выполняет фактическое завершение работы"""
        if self._shutting_down:
            return

        self._shutting_down = True
        print("Stopping all streams gracefully...")
        StreamRegistry.stop_all_streams()
        for stream in CamerasService.streams:
            stream.opened = False
            stream.destroy_output_container()
            Logger.warn(f'❌ {stream.camera.name} Force stop camera stream')

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
        print("Application starting up...")

        yield

        # Shutdown
        self._perform_shutdown()
        print("Application shutting down...")


# Глобальный экземпляр
lifespan_manager = LifespanManager()
