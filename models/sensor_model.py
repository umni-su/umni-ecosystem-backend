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
from pydantic import BaseModel

from models.sensor_history_model import SensorHistoryModel
from services.mqtt.topics.mqtt_sensor_type_enum import MqttSensorTypeEnum
from fastapi import UploadFile

from models.device_model import DeviceModelMain


class SensorModel(BaseModel):
    id: int | None = None
    device_id: int | None = None
    type: MqttSensorTypeEnum | None = None
    identifier: str
    name: str | None = None
    visible_name: str | None = None
    options: dict | None = None
    value: str | None = None
    photo: str | None = None
    last_sync: datetime | None = None


class SensorUpdateModel(BaseModel):
    id: int
    name: str | None = None
    cover: UploadFile | None = None


class SensorModelWithHistory(SensorModel):
    history: list[SensorHistoryModel]


class SensorModelWithDevice(SensorModel):
    device: DeviceModelMain = None
