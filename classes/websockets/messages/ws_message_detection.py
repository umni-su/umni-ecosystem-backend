from classes.websockets.messages.ws_message_base import WebsocketMessageBase
from classes.websockets.ws_message_topic import WebsocketMessageTopicEnum
from models.camera_model import CameraBaseModel


class WebsocketMessageDetection(WebsocketMessageBase):
    camera_id: int | None = None


class WebsocketMessageDetectionStart(WebsocketMessageDetection):
    topic: WebsocketMessageTopicEnum = WebsocketMessageTopicEnum.DETECTION_START


class WebsocketMessageDetectionEnd(WebsocketMessageDetection):
    topic: WebsocketMessageTopicEnum = WebsocketMessageTopicEnum.DETECTION_END
