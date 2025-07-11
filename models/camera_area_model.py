from pydantic import BaseModel

from entities.enums.event_priority_enum import EventPriorityEnum


class CameraAreaBaseModel(BaseModel):
    id: int | None = None
    name: str | None = None
    priority: EventPriorityEnum = EventPriorityEnum.ALERT
    active: bool = True
    points: list[(int, int)] | None = None
