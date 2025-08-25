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

from typing import Optional

from pydantic import BaseModel, Field

from entities.enums.event_priority_enum import EventPriorityEnum
from services.cameras.models.roi_settings import ROISettings


class CameraAreaModel(BaseModel):
    id: int | None = None
    name: str | None = None
    camera_id: int | None = None
    priority: EventPriorityEnum = EventPriorityEnum.ALERT
    active: bool = True
    color: str | None = None


class CameraAreaBaseModel(CameraAreaModel):
    points: list[list[int]] | None = None
    options: Optional[ROISettings] = Field(default=ROISettings)
