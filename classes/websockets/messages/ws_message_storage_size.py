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

import psutil
from pydantic import computed_field

from classes.websockets.messages.ws_message_base import WebsocketMessageBase
from classes.websockets.ws_message_topic import WebsocketMessageTopicEnum


class WebsocketMessageStorageSize(WebsocketMessageBase):
    topic: WebsocketMessageTopicEnum | None = WebsocketMessageTopicEnum.STORAGE_SIZE
    storage_id: int | None = None
    storage_path: str
    size: int = 0

    # # TODO calculate in separate thread and send data through websockets
    # @computed_field(return_type=int)
    # @property
    # def size(self):
    #     return Filesystem.get_size(self.storage_path)

    @computed_field
    @property
    def usage(self) -> dict:
        usage = psutil.disk_usage(self.storage_path)
        storage_percent = 100 * self.size / usage.total
        used_total = 100 * usage.used / usage.total
        return {
            "percent": usage.percent,
            "storage_percent": round(storage_percent, 2),
            "used_total": round(used_total, 2),
            "total": usage.total,
        }
