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

from typing import Annotated
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from websockets.exceptions import ConnectionClosed

from classes.auth.auth import Auth
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from classes.websockets.websockets import WebSockets
from responses.user import UserResponseOut

websockets = APIRouter(
    prefix='/ws',
    tags=['ws']
)


@websockets.websocket('/notifications')
async def websocket_endpoint(
        websocket: WebSocket,
        user: Annotated[UserResponseOut, Depends(Auth.validate_ws_token)],

):
    await WebSockets.add_client(websocket)
    Logger.debug(f'Add client [{user.username}] to server', LoggerType.WEBSOCKETS)

    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Message text was: {data}")
    except (WebSocketDisconnect, ConnectionClosed):
        Logger.debug(f'Client [{user.username}] closes connection', LoggerType.WEBSOCKETS)
        WebSockets.remove_client(websocket)
