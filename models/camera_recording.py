from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CameraRecordingBaseModel(BaseModel):
    camera_id: int
    start: datetime | None = None
    end: datetime | None = None
    duration: Optional[float] = None
    path: str | None = None
