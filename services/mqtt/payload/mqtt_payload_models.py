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

from pydantic import BaseModel, Field


# // TOPIC=manage/umni0a99f0/rel
# // DATA={"index":2,"level":1}

class MqttSensorPayloadModel(BaseModel):
    id: int
    value: float | int


class MqttManageRelayPayloadModel(BaseModel):
    index: int = Field(ge=0, le=24)
    level: int = Field(ge=0, lt=2)  # 0(LOW) or 1(HIGH)
