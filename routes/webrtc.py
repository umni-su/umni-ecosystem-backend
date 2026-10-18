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
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from websockets.exceptions import ConnectionClosed

from classes.auth.auth import Auth
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from classes.permissions.permission_dependency import check_permission
from classes.permissions.permission_manager import permission_manager
from config.settings import settings
from responses.user import UserResponseOut
from services.cameras.webrtc.manager import WebRTCManager
from services.cameras.webrtc.media_hub import MediaHubRegistry
from services.cameras.webrtc.session import PeerSession

# Одно мультиплексированное соединение на страницу: сообщения несут camera_id.
webrtc = APIRouter(prefix='/ws', tags=['webrtc'])

# REST-конфиг ICE для фронтенда
webrtc_config = APIRouter(prefix='/cameras', tags=['webrtc'])

VIEW_PERMISSION = 'cameras:view'

MIN_VIDEO_WIDTH = 16


def _normalize_width(value, default: int | None = None) -> int | None:
    """Приводит ширину видео к допустимому диапазону [MIN..settings].

    Возвращает None, если значение невалидно (сообщение можно игнорировать).
    """
    if isinstance(value, bool) or value is None:
        if default is None:
            return None
        value = default
    try:
        width = int(value)
    except (TypeError, ValueError):
        if default is None:
            return None
        width = default
    if width <= 0:
        if default is None:
            return None
        width = default
    return max(MIN_VIDEO_WIDTH, min(width, settings.WEBRTC_MAX_WIDTH))


@webrtc_config.get('/webrtc/config')
def get_webrtc_config(
        user: Annotated[UserResponseOut, Depends(check_permission(VIEW_PERMISSION))]
):
    urls = [url.strip() for url in (settings.WEBRTC_STUN_URLS or '').split(',') if url.strip()]
    ice_servers = [{"urls": urls}] if urls else []
    return {
        "ice_servers": ice_servers,
        "max_width": settings.WEBRTC_MAX_WIDTH,
        "default_width": settings.WEBRTC_DEFAULT_WIDTH,
    }


@webrtc.websocket('/webrtc')
async def webrtc_endpoint(
        websocket: WebSocket,
        user: Annotated[UserResponseOut, Depends(Auth.validate_ws_token)],
):
    if not permission_manager.has_permission(user.id, VIEW_PERMISSION):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    send_lock = asyncio.Lock()
    sessions: dict[str, PeerSession] = {}

    async def send(payload: dict) -> None:
        async with send_lock:
            await websocket.send_json(payload)

    async def close_session(session_id: str) -> None:
        session = sessions.pop(session_id, None)
        if session is None:
            return
        WebRTCManager.remove_session(session)
        await session.close()

    Logger.debug(f'WebRTC client [{user.username}] connected', LoggerType.WEBSOCKETS)

    try:
        while True:
            message = await websocket.receive_json()
            msg_type = message.get('type')

            if msg_type == 'offer':
                camera_id = int(message.get('camera_id'))
                session_id = str(message.get('session_id') or uuid.uuid4())
                hub = MediaHubRegistry.get(camera_id)
                if hub is None:
                    await send({
                        'type': 'error',
                        'session_id': session_id,
                        'camera_id': camera_id,
                        'message': 'camera stream not found',
                    })
                    continue

                # Разрешение видео на сессию (клип по settings.WEBRTC_MAX_WIDTH).
                # По умолчанию — settings.WEBRTC_DEFAULT_WIDTH (клиент может
                # поднять до максимума через set_width).
                video_width = _normalize_width(
                    message.get('width'),
                    default=settings.WEBRTC_DEFAULT_WIDTH,
                )

                # Пересоздаём сессию: закрываем и старую (по session_id), и
                # любые предыдущие сессии этой же камеры. Клиент генерит новый
                # session_id на каждый play, поэтому без этого накапливаются
                # незакрытые RTCPeerConnection — утечка ICE-портов сервера, из-за
                # которой новые соединения перестают подниматься вовсе.
                await close_session(session_id)
                for stale_id in [
                    sid for sid, existing in sessions.items()
                    if existing.camera_id == camera_id and sid != session_id
                ]:
                    await close_session(stale_id)
                session = PeerSession(
                    session_id=session_id,
                    camera_id=camera_id,
                    hub=hub,
                    send=send,
                    video_max_width=video_width,
                )
                sessions[session_id] = session
                WebRTCManager.add_session(session)

                try:
                    answer_sdp = await session.handle_offer(
                        message.get('sdp'),
                        message.get('sdp_type', 'offer'),
                    )
                except Exception as e:
                    Logger.err(f"WebRTC offer failed (camera {camera_id}): {e}", LoggerType.WEBSOCKETS)
                    await close_session(session_id)
                    await send({
                        'type': 'error',
                        'session_id': session_id,
                        'camera_id': camera_id,
                        'message': str(e),
                    })
                    continue

                await send({
                    'type': 'answer',
                    'session_id': session_id,
                    'camera_id': camera_id,
                    'sdp': answer_sdp,
                    'sdp_type': 'answer',
                })

            elif msg_type == 'set_width':
                # Смена разрешения на лету, без пересоединения
                session = sessions.get(str(message.get('session_id') or ''))
                if session is not None:
                    width = _normalize_width(message.get('width'))
                    if width is not None:
                        session.set_video_width(width)

            elif msg_type == 'close':
                await close_session(str(message.get('session_id') or ''))

            elif msg_type == 'ping':
                await send({'type': 'pong'})

    except (WebSocketDisconnect, ConnectionClosed):
        Logger.debug(f'WebRTC client [{user.username}] disconnected', LoggerType.WEBSOCKETS)
    except Exception as e:
        Logger.err(f"WebRTC signaling error: {e}", LoggerType.WEBSOCKETS)
    finally:
        for session_id in list(sessions.keys()):
            await close_session(session_id)
