from datetime import datetime
from pydantic import BaseModel


class SensorHistoryModel(BaseModel):
    id: int
    sensor_id: int
    value: str
    created: datetime


class SensorHistoryChartModel(BaseModel):
    value: str
    created: datetime
