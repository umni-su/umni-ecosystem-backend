from classes.websockets.messages.ws_message_base import WebsocketMessageBase
from classes.websockets.ws_message_topic import WebsocketMessageTopicEnum


class WebsocketMessageStorageSize(WebsocketMessageBase):
    topic: WebsocketMessageTopicEnum | None = WebsocketMessageTopicEnum.STORAGE_SIZE
    storage_id: int | None = None
    size: int = 0
