from enum import StrEnum


class WebsocketMessageTopicEnum(StrEnum):
    DETECTION_START = 'detection.start'
    DETECTION_END = 'detection.end'
