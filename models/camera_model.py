from pydantic import BaseModel, Field, computed_field

from entities.enums.camera_protocol_enum import CameraProtocolEnum
from entities.enums.camera_record_type_enum import CameraRecordTypeEnum
from models.camera_area_model import CameraAreaBaseModel
from models.storage_model import StorageModel


class CameraGetModel(BaseModel):
    id: int | None = None
    storage_id: int
    name: str


class CameraBaseModel(CameraGetModel):
    active: bool = True
    alerts: bool = True
    record: bool = False
    record_duration: int | None = None
    record_mode: CameraRecordTypeEnum | None = None
    delete_after: int | None = None
    cover: str | None = None
    protocol: CameraProtocolEnum
    ip: str | None = None
    port: int | None = None
    username: str | None = None
    password: str | None = Field(exclude=True)
    primary: str | None = None
    secondary: str | None = None
    change_credentials: bool = False

    @computed_field
    @property
    def has_credentials(self) -> bool:
        return True if (self.password is not None or self.username is not None) else False


class CameraModelWithRelations(CameraBaseModel):
    # location:
    storage: StorageModel | None = None
    areas: list[CameraAreaBaseModel] | None = None
