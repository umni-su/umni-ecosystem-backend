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

from classes.websockets.messages.ws_message_base import WebsocketMessageBase
from classes.websockets.ws_message_topic import WebsocketMessageTopicEnum


class WebsocketMessageDetection(WebsocketMessageBase):
    camera_id: int | None = None
    area_id: int | None = None


class WebsocketMessageDetectionStart(WebsocketMessageDetection):
    topic: WebsocketMessageTopicEnum = WebsocketMessageTopicEnum.DETECTION_START


class WebsocketMessageDetectionEnd(WebsocketMessageDetection):
    topic: WebsocketMessageTopicEnum = WebsocketMessageTopicEnum.DETECTION_END
