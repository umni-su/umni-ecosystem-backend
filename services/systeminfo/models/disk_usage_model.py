from pydantic import BaseModel


class DiskUsage(BaseModel):
    total: int = 0
    used: int = 0
    free: int = 0
