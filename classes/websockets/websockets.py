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
import json
import threading
from concurrent.futures import Future
from typing import Optional
from fastapi import WebSocket

from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from classes.websockets.messages.ws_message_base import WebsocketMessageBase


class WebSockets:
    clients: set[WebSocket] = set()
    # Единственный серверный event loop. WebSocket нельзя отправлять из чужого
    # event loop (asyncio.run в отдельном потоке на каждый send создавал новый
    # loop и приводил к гонкам и крашам BaseEventLoop.__del__ при завершении).
    _loop: Optional[asyncio.AbstractEventLoop] = None
    _loop_lock = threading.Lock()

    @classmethod
    def set_loop(cls, loop: asyncio.AbstractEventLoop) -> None:
        with cls._loop_lock:
            cls._loop = loop

    @classmethod
    def clear_loop(cls) -> None:
        with cls._loop_lock:
            cls._loop = None

    @classmethod
    async def add_client(cls, ws: WebSocket):
        await ws.accept()
        cls.clients.add(ws)

    @classmethod
    def remove_client(cls, ws: WebSocket):
        cls.clients.discard(ws)

    @classmethod
    def send(cls, ws: WebSocket, data: dict | str | WebsocketMessageBase):
        if isinstance(data, WebsocketMessageBase):
            data = data.model_dump_json()
        elif isinstance(data, dict):
            data = json.dumps(data)

        loop = cls._loop
        if loop is None or loop.is_closed():
            Logger.warn(
                "WebSockets event loop is unavailable, message dropped",
                LoggerType.WEBSOCKETS
            )
            return

        try:
            # Планируем send в серверном loop из любого потока
            future = asyncio.run_coroutine_threadsafe(ws.send_text(data), loop)
            future.add_done_callback(cls._on_send_done)
        except RuntimeError as e:
            Logger.err(f"WebSockets send failed: {e}", LoggerType.WEBSOCKETS)

    @staticmethod
    def _on_send_done(future: Future) -> None:
        if future.cancelled():
            return
        exc = future.exception()
        if exc is not None:
            Logger.debug(f"WebSocket send dropped: {exc}", LoggerType.WEBSOCKETS)

    @classmethod
    def send_broadcast(cls, data: dict | str | WebsocketMessageBase):
        if isinstance(data, WebsocketMessageBase):
            data = data.model_dump_json()
        elif isinstance(data, dict):
            data = json.dumps(data)
        for cl in list(cls.clients):
            cls.send(cl, data)
