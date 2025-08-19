from classes.websockets.messages.ws_message_base import WebsocketMessageBase
from classes.websockets.ws_message_topic import WebsocketMessageTopicEnum


class WebsocketMessageDetection(WebsocketMessageBase):
    camera_id: int | None = None
    area_id: int | None = None


class WebsocketMessageDetectionStart(WebsocketMessageDetection):
    topic: WebsocketMessageTopicEnum = WebsocketMessageTopicEnum.DETECTION_START


class WebsocketMessageDetectionEnd(WebsocketMessageDetection):
    topic: WebsocketMessageTopicEnum = WebsocketMessageTopicEnum.DETECTION_END
