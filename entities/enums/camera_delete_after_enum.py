from enum import Enum


class CameraDeleteAfterEnum(Enum):
    HOUR = 60,
    DAY = 60 * 24
    TWO_DAYS = 60 * 24 * 2
    THREE_DAYS = 60 * 24 * 3
    FIVE_DAYS = 60 * 24 * 5
    WEEK = 60 * 24 * 7
    MONTH = 60 * 24 * 30
    YEAR = 60 * 24 * 365
