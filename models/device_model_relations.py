# Copyright (C) 2025 Mikhail Sazanov
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from pydantic import ConfigDict
from models.device_model import DeviceModel
from models.device_netif import DeviceNetif
from models.sensor_model import SensorModel


class DeviceModelWithSensors(DeviceModel):
    sensors: list[SensorModel] | None = None


class DeviceModelWithNetif(DeviceModel):
    network_interfaces: list[DeviceNetif] | None = None


class DeviceModelWithRelations(DeviceModelWithSensors, DeviceModelWithNetif):
    model_config = ConfigDict(
        from_attributes=True
    )
