from datetime import datetime

from pydantic import BaseModel, Field

from entities.enums.camera_record_type_enum import CameraRecordTypeEnum
from models.camera_area_model import CameraAreaModel
from models.camera_model import CameraGetModel
from models.camera_recording import CameraRecordingModel
from services.cameras.classes.roi_tracker import ROIEventType


class CameraEventPost(BaseModel):
    area_id: int
    camera_id: int
    type: CameraRecordTypeEnum | None
    start: datetime | None = Field(default=None)
    end: datetime | None = Field(default=None)


class CameraEventModelRelations(BaseModel):
    area: CameraAreaModel | None = None
    recording: CameraRecordingModel | None = None
    camera: CameraGetModel | None = None


class CameraEventBaseModel(CameraEventModelRelations):
    id: int
    area_id: int | None = None
    type: CameraRecordTypeEnum | None
    duration: float | None = None
    start: datetime | None = Field(default=None)
    end: datetime | None = Field(default=None)


class CameraEventModel(CameraEventBaseModel):
    resized: str
    original: str | None = None
    action: ROIEventType | None
