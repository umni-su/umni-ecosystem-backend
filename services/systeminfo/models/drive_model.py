from pydantic import BaseModel

from services.systeminfo.models.disk_usage_model import DiskUsage


class DriveModelBase(BaseModel):
    device: str | None = None
    mountpoint: str | None = None
    stat: DiskUsage | None = None


class DriveModel(DriveModelBase):
    fstype: str | None = None
    opts: list[str] | None = None
