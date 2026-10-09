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
from typing import Awaitable, Callable, Optional

from aiortc import (
    RTCConfiguration,
    RTCIceServer,
    RTCPeerConnection,
    RTCSessionDescription,
)

from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from config.settings import settings
from services.cameras.webrtc.media_hub import CameraMediaHub
from services.cameras.webrtc.tracks import HubAudioTrack, HubVideoTrack

SendCallable = Callable[[dict], Awaitable[None]]


def build_rtc_configuration() -> RTCConfiguration:
    """Собирает RTCConfiguration из настроек (по умолчанию — только LAN)."""
    ice_servers: list[RTCIceServer] = []
    urls = [url.strip() for url in (settings.WEBRTC_STUN_URLS or '').split(',') if url.strip()]
    if urls:
        ice_servers.append(RTCIceServer(urls=urls))
    return RTCConfiguration(iceServers=ice_servers)


class PeerSession:
    """Одна WebRTC-сессия зрителя для одной камеры."""

    def __init__(
            self,
            session_id: str,
            camera_id: int,
            hub: CameraMediaHub,
            send: SendCallable,
    ):
        self.session_id = session_id
        self.camera_id = camera_id
        self.hub = hub
        self._send = send
        self._closed = False

        self.pc = RTCPeerConnection(configuration=build_rtc_configuration())
        self.video = HubVideoTrack(hub)
        self.audio = HubAudioTrack(hub)
        self.pc.addTrack(self.video)
        self.pc.addTrack(self.audio)

        @self.pc.on("icecandidate")
        def on_icecandidate(candidate) -> None:
            # При non-trickle кандидаты уже в SDP ответа; событие игнорируем.
            if candidate is not None:
                Logger.debug(
                    f"[webrtc][{self.camera_id}] local candidate: {candidate.ip}:{candidate.port}",
                    LoggerType.CAMERAS,
                )

        @self.pc.on("connectionstatechange")
        async def on_connectionstatechange() -> None:
            state = self.pc.connectionState
            Logger.debug(f"[webrtc][{self.camera_id}] connection state: {state}", LoggerType.CAMERAS)
            await self._emit({"type": "state", "state": state})
            if state in ("failed", "closed"):
                await self.close()

    async def handle_offer(self, sdp: str, sdp_type: str = "offer") -> str:
        """Принимает offer клиента, возвращает SDP-answer (non-trickle)."""
        await self.pc.setRemoteDescription(RTCSessionDescription(sdp=sdp, type=sdp_type))
        answer = await self.pc.createAnswer()
        # setLocalDescription дожидается сбора ICE-кандидатов, поэтому
        # localDescription.sdp уже содержит все candidate-строки.
        await self.pc.setLocalDescription(answer)
        return self.pc.localDescription.sdp

    async def _emit(self, payload: dict) -> None:
        if self._closed:
            return
        payload["session_id"] = self.session_id
        payload["camera_id"] = self.camera_id
        try:
            await self._send(payload)
        except Exception as e:
            Logger.debug(f"[webrtc][{self.camera_id}] send failed: {e}", LoggerType.CAMERAS)

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            await self.video.close()
        except Exception:
            pass
        try:
            await self.audio.close()
        except Exception:
            pass
        try:
            await self.pc.close()
        except Exception:
            pass
