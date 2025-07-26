from typing import Optional, List

from pydantic import BaseModel

from services.scheduler.enums.schedule_frequency import ScheduleFrequency


class TaskSchedule(BaseModel):
    frequency: ScheduleFrequency
    interval: int = 1
    at_time: Optional[str] = None  # Формат "HH:MM"
