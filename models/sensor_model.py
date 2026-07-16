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
from typing import Optional, Union

from pydantic import BaseModel, Field

from models.sensor_history_model import SensorHistoryModel
from classes.devices.device_sensor_type_enum import DeviceSensorTypeEnum
from fastapi import UploadFile

from models.device_model import DeviceModelMain


class SensorCreateModel(BaseModel):
    device_id: int
    type: DeviceSensorTypeEnum
    capability: str
    identifier: str
    active: bool
    name: Optional[str] = None
    visible_name: Optional[str] = None
    options: Optional[dict] = None
    value: Optional[str] = None
    photo: Optional[str] = None
    last_sync: Optional[datetime] = None
    unit: Optional[str] = None
    icon: Optional[str] = None

    class Config:
        extra = 'ignore'


class SensorModel(SensorCreateModel):
    id: int | None = None


class SensorUpdateModel(SensorModel):
    pass


class SensorModelWithHistory(SensorModel):
    history: list[SensorHistoryModel]


class SensorModelWithDevice(SensorModel):
    device: DeviceModelMain = None


class SensorPayload(BaseModel):
    value: Optional[Union[int | float | str | bool]]
