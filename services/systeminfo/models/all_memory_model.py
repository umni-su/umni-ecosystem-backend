from pydantic import BaseModel

from services.systeminfo.models.memory_stat_model import MemoryModel, MemoryModelBase


class AllMemoryModelMinimized(BaseModel):
    swap: MemoryModelBase | None = None
    virtual: MemoryModelBase | None = None


class AllMemoryModel(BaseModel):
    swap: MemoryModel | None = None
    virtual: MemoryModel | None = None
