from datetime import datetime

from pydantic import BaseModel, Field

from entities.enums.camera_record_type_enum import CameraRecordTypeEnum


class CameraEventPost(BaseModel):
    area_id: int
    type: CameraRecordTypeEnum | None
    start: datetime | None = Field(default=None)
    end: datetime | None = Field(default=None)
