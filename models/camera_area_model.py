from typing import Optional

from pydantic import BaseModel, Field

from entities.enums.event_priority_enum import EventPriorityEnum
from services.cameras.classes.roi_tracker import ROISettings


class CameraAreaBaseModel(BaseModel):
    id: int | None = None
    name: str | None = None
    priority: EventPriorityEnum = EventPriorityEnum.ALERT
    active: bool = True
    color: str | None = None
    points: list[list[int]] | None = None
    options: Optional[ROISettings] = Field(default_factory=ROISettings)
