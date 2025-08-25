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

from pydantic import BaseModel

from services.systeminfo.models.all_memory_model import AllMemoryModel
from services.systeminfo.models.cpu_model import CpuModel
from services.systeminfo.models.drive_model import DriveModelBase
from services.systeminfo.models.net_usage_model import NetUsageModel


class SysteminfoModel(BaseModel):
    disks: list[DriveModelBase]
    memory: AllMemoryModel
    cpu: CpuModel
    net: NetUsageModel
