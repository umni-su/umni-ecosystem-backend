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

from pydantic import BaseModel, ConfigDict

from models.device_netif import DeviceNetif
from models.sensor_model import SensorModel


class DeviceModel(BaseModel):
    id: int | None = None
    name: str | None = None
    title: str | None = None
    description: str | None = None
    location_id: int | None = None
    photo: str | None = None
    type: int | None = None
    online: bool | None = None
    uptime: int | None = None
    free_heap: int | None = None
    total_heap: int | None = None
    fw_ver: str | None = None
    last_sync: datetime | None = None
    created: datetime | None = None
    updated: datetime | None = None


class DeviceUpdateModel(BaseModel):
    id: int | None = None
    title: str | None = None


class DeviceModelWithSensors(DeviceModel):
    sensors: list[SensorModel] | None = None


class DeviceModelWithNetif(DeviceModel):
    network_interfaces: list[DeviceNetif] | None = None


class DeviceModelWithRelations(DeviceModelWithSensors, DeviceModelWithNetif):
    model_config = ConfigDict(
        from_attributes=True
    )
