from datetime import datetime

from pydantic import BaseModel


class DeviceNetif(BaseModel):
    id: int
    device_id: int | None = None
    name: str
    mac: str
    ip: str
    mask: str
    gw: str
    last_sync: datetime | None = None
