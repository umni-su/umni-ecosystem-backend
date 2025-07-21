from datetime import datetime

from pydantic import BaseModel, Field

from entities.enums.camera_record_type_enum import CameraRecordTypeEnum
from models.camera_area_model import CameraAreaModel


class CameraEventPost(BaseModel):
    area_id: int
    camera_id: int
    type: CameraRecordTypeEnum | None
    start: datetime | None = Field(default=None)
    end: datetime | None = Field(default=None)


class CameraEventRelations(BaseModel):
    area: CameraAreaModel | None = None


class CameraEventModel(CameraEventRelations):
    id: int
    screenshot: str
    file: str | None = None
    type: CameraRecordTypeEnum | None
    start: datetime | None = Field(default=None)
    end: datetime | None = Field(default=None)
