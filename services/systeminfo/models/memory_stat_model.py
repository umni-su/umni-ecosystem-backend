from pydantic import BaseModel


class MemoryModelBase(BaseModel):
    percent: float = 0.0
    values: list[float] = []


class MemoryModel(MemoryModelBase):
    total: int = 0
    used: int = 0
    free: int = 0
