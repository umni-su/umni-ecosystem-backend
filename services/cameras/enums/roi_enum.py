from enum import Enum


class ROIEventType(Enum):
    MOTION_START = 1
    MOTION_END = 2
    ROI_DETECT_START = 3
    ROI_DETECT_END = 4
    STATIC_VIDEO = 5
    STATIC_SCREENSHOT = 6
