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
from enum import Enum


class LogCode(Enum):
    DEVICE_REGISTERED = 1
    DEVICE_ONLINE = 2
    DEVICE_OFFLINE = 3
    CAMERA_ONLINE = 4
    CAMERA_OFFLINE = 5
    CAMERA_MOTION_START = 6
    CAMERA_MOTION_END = 7
    SENSOR_DATA = 8
