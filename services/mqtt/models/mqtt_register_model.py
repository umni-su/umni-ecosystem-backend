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

from services.mqtt.models.mqtt_heap_model import MqttHeapModel
from services.mqtt.models.mqtt_netif_model import MqttNetifModel


class MqttRegisterModel(BaseModel):
    hostname: str
    fw_ver: Optional[str] = Field(None)
    capabilities: list[str]
    networks: list[MqttNetifModel]
    heap: Optional[MqttHeapModel] = Field(default=None)
    device_type: Optional[str] = Field(default=None)
    uptime: Optional[int] = Field(default=None)
    reset_reason: Optional[int] = Field(default=None)
