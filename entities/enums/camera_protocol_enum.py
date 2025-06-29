from enum import StrEnum


class CameraProtocolEnum(StrEnum):
    RTSP = 'RTSP'
    RTMP = 'RTMP'
    HTTP = 'HTTP'
    HTTPS = 'HTTPS'
    USB = 'USB'
