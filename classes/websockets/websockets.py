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
from threading import Thread
from fastapi import WebSocket

from classes.websockets.messages.ws_message_base import WebsocketMessageBase


class WebSockets:
    clients: set[WebSocket] = set()

    @classmethod
    async def add_client(cls, ws: WebSocket):
        await ws.accept()
        cls.clients.add(ws)

    @classmethod
    def remove_client(cls, ws: WebSocket):
        cls.clients.remove(ws)

    @classmethod
    def send(cls, ws: WebSocket, data: dict | str | WebsocketMessageBase):
        if isinstance(data, WebsocketMessageBase):
            data = data.model_dump_json()
        thread: Thread = Thread(target=asyncio.run, args=[ws.send_text(data)])
        thread.start()
        # await ws.send_json(data)

    @classmethod
    def send_broadcast(cls, data: dict | str | WebsocketMessageBase):
        for cl in cls.clients:
            cls.send(cl, data)
