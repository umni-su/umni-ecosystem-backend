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
import threading
from typing import Optional

from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from services.cameras.webrtc.session import PeerSession


class WebRTCManager:
    """Реестр активных WebRTC-сессий для корректного завершения приложения."""

    _sessions: set[PeerSession] = set()
    _lock = threading.Lock()
    _loop: Optional[asyncio.AbstractEventLoop] = None

    @classmethod
    def set_loop(cls, loop: asyncio.AbstractEventLoop) -> None:
        cls._loop = loop

    @classmethod
    def clear_loop(cls) -> None:
        cls._loop = None

    @classmethod
    def add_session(cls, session: PeerSession) -> None:
        with cls._lock:
            cls._sessions.add(session)

    @classmethod
    def remove_session(cls, session: PeerSession) -> None:
        with cls._lock:
            cls._sessions.discard(session)

    @classmethod
    def sessions_snapshot(cls) -> list[PeerSession]:
        with cls._lock:
            return list(cls._sessions)

    @classmethod
    def shutdown(cls) -> None:
        """Закрывает все активные сессии (вызывается при завершении приложения)."""
        sessions = cls.sessions_snapshot()
        with cls._lock:
            cls._sessions.clear()
        if not sessions:
            return

        loop = cls._loop
        for session in sessions:
            try:
                if loop is not None and loop.is_running() and not loop.is_closed():
                    asyncio.run_coroutine_threadsafe(session.close(), loop)
                else:
                    Logger.debug(
                        f"[webrtc] event loop unavailable, session {session.session_id} left to GC",
                        LoggerType.CAMERAS,
                    )
            except Exception as e:
                Logger.debug(f"[webrtc] failed to close session: {e}", LoggerType.CAMERAS)
