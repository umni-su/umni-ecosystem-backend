from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CameraRecordingModel(BaseModel):
    id: int | None = None
    camera_id: int | None = None
    start: datetime | None = None
    end: datetime | None = None
    duration: Optional[float] = None
    path: str | None = None
