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
