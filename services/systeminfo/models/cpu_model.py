from pydantic import BaseModel


class CpuModel(BaseModel):
    last: float = 0.0
    values: list[float] = []
