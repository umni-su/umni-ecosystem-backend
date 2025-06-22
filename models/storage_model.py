from pydantic import BaseModel, computed_field

from classes.storages.filesystem import Filesystem


class StorageModelBase(BaseModel):
    name: str
    path: str
    active: bool = None

    # TODO calculate in separate thread and send data through websockets
    @computed_field(return_type=int)
    @property
    def size(self):
        return Filesystem.get_size(self.path)


class StorageModel(StorageModelBase):
    id: int
