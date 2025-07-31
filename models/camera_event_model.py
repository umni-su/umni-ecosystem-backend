from datetime import datetime, timedelta

from pydantic import BaseModel, Field

from entities.enums.camera_record_type_enum import CameraRecordTypeEnum
from models.camera_area_model import CameraAreaModel
from models.camera_model import CameraGetModel
from models.camera_recording import CameraRecordingBaseModel
from services.cameras.classes.roi_tracker import ROIEventType


class CameraEventPost(BaseModel):
    area_id: int
    camera_id: int
    type: CameraRecordTypeEnum | None
    start: datetime | None = Field(default=None)
    end: datetime | None = Field(default=None)


class CameraEventModelRelations(BaseModel):
    area: CameraAreaModel | None = None
    recording: CameraRecordingBaseModel | None = None
    camera: CameraGetModel | None = None


class CameraEventBase(CameraEventModelRelations):
    id: int
    type: CameraRecordTypeEnum | None
    duration: float | None = None
    start: datetime | None = Field(default=None)
    end: datetime | None = Field(default=None)


class CameraEventModel(CameraEventBase):
    resized: str
    original: str | None = None
    action: ROIEventType | None
