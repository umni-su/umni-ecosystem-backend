from pydantic import BaseModel

from entities.enums.camera_delete_after_enum import CameraDeleteAfterEnum
from entities.enums.camera_protocol_enum import CameraProtocolEnum
from models.storage_model import StorageModel


class CameraBaseModel(BaseModel):
    id: int
    name: str
    record: bool
    record_duration: int | None = None
    delete_after: CameraDeleteAfterEnum | None = None
    cover: str | None = None
    protocol: CameraProtocolEnum | None = None
    ip: str | None = None
    port: int | None = None
    username: str | None = None
    password: str | None = None
    primary: str | None = None
    secondary: str | None = None


class CameraModelWithRelations(CameraBaseModel):
    # location:
    storage: StorageModel
