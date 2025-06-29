import asyncio
from threading import Thread
from typing import Annotated
import cv2
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, WebSocketException
from websockets.exceptions import ConnectionClosed

from classes.auth.auth import Auth
from classes.logger import Logger
from classes.websockets.websockets import WebSockets
from entities.camera import CameraEntity
from repositories.camera_repository import CameraRepository
from responses.user import UserResponseOut
from services.cameras.cameras_service import CamerasService

connected_clients: list[WebSocket] = []

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
    Logger.warn(f'Add client [{user.username}] to server')

    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Message text was: {data}")
    except (WebSocketDisconnect, ConnectionClosed):
        Logger.warn(f'Client [{user.username}] closes connection')
        WebSockets.remove_client(websocket)


@websockets.websocket('/cameras/{camera_id}/stream')
async def get_cameras(
        websocket: WebSocket,
        user: Annotated[UserResponseOut, Depends(Auth.validate_token)],
        camera: CameraEntity = Depends(CameraRepository.get_camera)
):
    await websocket.accept()
    connected_clients.append(websocket)

    for stream in CamerasService.streams:
        if stream.id == camera.id:
            try:
                while True:
                    _, encoded_frame = cv2.imencode('.jpg', stream.resized)
                    frame_data = encoded_frame.tobytes()
                    await websocket.send_bytes(frame_data)
                    # asyncio.run()
            except (WebSocketDisconnect, ConnectionClosed):
                await websocket.close(code=1001)
                Logger.debug(f'[WebSocketDisconnect] Client {user.username} disconnects')
            except Exception as e:
                await websocket.close(code=1001)
                Logger.err(e)
            print('While end')
