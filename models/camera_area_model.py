from typing import TypedDict

from pydantic import BaseModel

from entities.enums.event_priority_enum import EventPriorityEnum


class CameraAreaPoint(TypedDict):
    x: int
    y: int


class CameraAreaBaseModel(BaseModel):
    id: int | None = None
    name: str | None = None
    priority: EventPriorityEnum = EventPriorityEnum.ALERT
    active: bool = True
    color: str | None = None
    points: list[CameraAreaPoint] | None = None
