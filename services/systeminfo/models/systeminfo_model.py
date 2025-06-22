from pydantic import BaseModel

from services.systeminfo.models.all_memory_model import AllMemoryModel
from services.systeminfo.models.drive_model import DriveModelBase
from services.systeminfo.models.net_usage_model import NetUsageModel


class SysteminfoModel(BaseModel):
    disks: list[DriveModelBase]
    memory: AllMemoryModel
    cpu: float
    net: NetUsageModel
