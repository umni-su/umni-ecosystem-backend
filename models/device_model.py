from datetime import datetime

from pydantic import BaseModel

from models.device_netif import DeviceNetif
from models.sensor_model import SensorModel


class DeviceModel(BaseModel):
    id: int | None = None
    name: str | None = None
    title: str | None = None
    description: str | None = None
    photo: str | None = None
    type: int | None = None
    online: bool | None = None
    uptime: int | None = None
    free_heap: int | None = None
    total_heap: int | None = None
    fw_ver: str | None = None
    last_sync: datetime | None = None


class DeviceUpdateModel(BaseModel):
    id: int | None = None
    title: str | None = None


class DeviceModelWithSensors(DeviceModel):
    sensors: list[SensorModel] | None = None


class DeviceModelWithNetif(DeviceModel):
    network_interfaces: list[DeviceNetif] | None = None


class DeviceModelWithRelations(DeviceModelWithSensors, DeviceModelWithNetif):
    pass
