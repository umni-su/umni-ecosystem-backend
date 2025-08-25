#  Copyright (C) 2025 Mikhail Sazanov
#  #
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#  #
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#  #
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

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
