from datetime import datetime

from pydantic import BaseModel, Field

from classes.websockets.ws_message_topic import WebsocketMessageTopicEnum


class WebsocketMessageBase(BaseModel):
    topic: WebsocketMessageTopicEnum | None = None
    date: datetime = Field(default_factory=datetime.now)
    message: str | None = None
