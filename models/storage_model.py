from pydantic import BaseModel


class StorageModelBase(BaseModel):
    name: str
    path: str
    active: bool = None


class StorageModel(StorageModelBase):
    id: int
