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

import io
import zipfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
import os
from typing import Annotated

from classes.auth.auth import Auth
from classes.logger import Logger
from models.camera_event_model import CameraEventModel
from repositories.camera_events_repository import CameraEventsRepository
from responses.success import SuccessResponse
from responses.user import UserResponseOut

events = APIRouter(
    prefix='/events',
    tags=['events']
)


@events.get("/{event_id}", response_model=CameraEventModel)
async def stream_video(
        event_id: int,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    event = CameraEventsRepository.get_event(event_id, True)
    return event


@events.delete("/{event_id}", response_model=SuccessResponse)
async def stream_video(
        event_id: int,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    event: CameraEventsRepository.delete_event(event_id)
    return SuccessResponse(
        success=True
    )


@events.get("/{event_id}/download")
async def download_camera_event(
        event_id: int,
        user: Annotated[UserResponseOut, Depends(Auth.validate_token)],
):
    try:
        event = CameraEventsRepository.get_event(event_id, True)

        # Предположим, у нас есть пути к файлам события
        screenshot_path = Path(event.resized)
        original_path = Path(event.original)
        recording_path = None
        if event.recording is not None:
            recording_path = Path(event.recording.path)

            # Проверяем существование файлов
            if not recording_path.exists():
                raise HTTPException(status_code=404, detail="Recording file not found")

        # Проверяем остальные файлы, если нужен zip
        if not (screenshot_path.exists() and original_path.exists()):
            raise HTTPException(status_code=404, detail="Some event files not found")

        # Создаем zip-архив в памяти
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zip_file:
            # Добавляем файлы в архив
            zip_file.write(screenshot_path, arcname=os.path.basename(screenshot_path))
            zip_file.write(original_path, arcname=os.path.basename(original_path))
            if recording_path is not None:
                zip_file.write(recording_path, arcname=os.path.basename(recording_path))

        # Перемещаем указатель в начало буфера
        zip_buffer.seek(0)

        name = datetime.now().strftime(f'Cam-{event.camera.id}-Event-{event.id}-%Y-%m-%d_%H-%M-%S-%f')

        # Возвращаем архив как поток
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={name}.zip",
                "Content-Length": str(zip_buffer.getbuffer().nbytes)
            }
        )
    except Exception as e:
        Logger.err(f'Error download event {str(e)}')
        raise HTTPException(
            status_code=500,
            detail='Error download event'
        )


@events.get("/{event_id}/play")
async def stream_video(
        event_id: int,
        request: Request,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    event = CameraEventsRepository.get_event(event_id, True)
    if not event or not event.recording:
        raise HTTPException(status_code=404, detail="Event has no recording")

    video_path = event.recording.path

    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video not found")

    # Добавляем проверку MIME-типа
    ext = os.path.splitext(video_path)[1].lower()
    mime_type = {
        '.mp4': 'video/mp4',
        '.avi': 'video/x-msvideo',
        '.mov': 'video/quicktime'
    }.get(ext, 'application/octet-stream')

    file_size = os.path.getsize(video_path)
    start = 0
    end = file_size - 1

    range_header = request.headers.get("range")
    if range_header:
        start, end = parse_range_header(range_header, file_size)

    content_length = end - start + 1
    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Type": mime_type,
        "Content-Disposition": "inline"  # Важно для воспроизведения в браузере
    }

    def file_iterator():
        with open(video_path, "rb") as f:
            f.seek(start)
            remaining = content_length
            while remaining > 0:
                chunk_size = min(1024 * 1024, remaining)  # 1MB chunks
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    return StreamingResponse(
        file_iterator(),
        headers=headers,
        status_code=206 if range_header else 200,
        media_type=mime_type
    )


def parse_range_header(range_header: str, file_size: int) -> tuple:
    bytes_ = range_header.replace("bytes=", "").split("-")
    start = int(bytes_[0]) if bytes_[0] else 0
    end = int(bytes_[1]) if bytes_[1] else file_size - 1
    return start, end
