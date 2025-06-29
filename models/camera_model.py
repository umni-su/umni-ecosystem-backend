from pydantic import BaseModel

from entities.enums.camera_protocol_enum import CameraProtocolEnum
from models.storage_model import StorageModel


class CameraBaseModel(BaseModel):
    id: int | None = None
    storage_id: int
    name: str
    active: bool = True
    record: bool = False
    record_duration: int | None = None
    delete_after: int | None = None
    cover: str | None = None
    protocol: CameraProtocolEnum
    ip: str | None = None
    port: int | None = None
    username: str | None = None
    password: str | None = None
    primary: str | None = None
    secondary: str | None = None


class CameraModelWithRelations(CameraBaseModel):
    # location:
    storage: StorageModel | None = None
