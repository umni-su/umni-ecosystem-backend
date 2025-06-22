from pydantic import BaseModel


class MemoryModelBase(BaseModel):
    percent: float


class MemoryModel(MemoryModelBase):
    total: int
    used: int
    free: int
