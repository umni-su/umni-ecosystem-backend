from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CameraRecordingModel(BaseModel):
    camera_id: int
    start: datetime | None = None
    end: datetime | None = None
    duration: Optional[float] = None
    path: str | None = None
