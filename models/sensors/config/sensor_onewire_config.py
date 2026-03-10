# Copyright (C) 2026 Mikhail Sazanov
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
from typing import Optional

from pydantic import BaseModel, Field


class SensorOnewireConfigItem(BaseModel):
    sn: str = Field(...)
    label: Optional[str] = Field(default=None)
    active: Optional[bool] = Field(default=False)


class SensorOneWireConfig(BaseModel):
    sensors: list[SensorOnewireConfigItem] = Field(default_factory=list)
