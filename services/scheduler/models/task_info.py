from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class TaskStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ERROR = "ERROR"


class TaskInfo(BaseModel):
    name: str
    status: TaskStatus
    next_run: Optional[datetime]
    frequency: str
    interval: int
    at_time: Optional[str]
    last_run: Optional[datetime]
    last_result: Optional[str]
