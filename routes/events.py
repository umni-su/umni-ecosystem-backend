from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.responses import StreamingResponse, FileResponse
import os
from typing import Annotated

from models.camera_event_model import CameraEventModel
from repositories.camera_events_repository import CameraEventsRepository

events = APIRouter(
    prefix='/events',
    tags=['events']
)


@events.get("/{event_id}/play")
async def stream_video(
        request: Request,
        # user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        event: Annotated[CameraEventModel, Depends(CameraEventsRepository.get_event)]
):
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
