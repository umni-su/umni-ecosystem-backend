import datetime

import cv2
from typing import List, TYPE_CHECKING
import numpy as np
from pydantic import BaseModel, field_validator, Field, ConfigDict
from services.cameras.enums.roi_enum import ROIEventType

if TYPE_CHECKING:
    from models.camera_model import CameraModelWithRelations


class ROISettings(BaseModel):
    """
    Настройки детекции для ROI
    Attributes:
        enabled (bool): Включена ли детекция
        sensitivity (float): Чувствительность (0.1-5.0), где 0.1 - максимальная чувствительность, 5.0 - минимальная
        min_area (int): Минимальная площадь контура
        min_aspect_ratio (float): Минимальное соотношение сторон
        max_aspect_ratio (float): Максимальное соотношение сторон
    """
    enabled: bool = True
    sensitivity: float = Field(1.4, ge=0.1, le=5.0)
    min_area: int = Field(100, gt=0)
    min_aspect_ratio: float = Field(0.5, gt=0)
    max_aspect_ratio: float = Field(2.0, gt=0)

    @classmethod
    @field_validator('max_aspect_ratio')
    def validate_aspect_ratios(cls, v, values):
        if 'min_aspect_ratio' in values and v < values['min_aspect_ratio']:
            raise ValueError("max_aspect_ratio must be >= min_aspect_ratio")
        return v


class ROI(BaseModel):
    """
    Область интереса (Region of Interest)
    Attributes:
        id (int): Уникальный идентификатор
        name (str): Название области
        points (List[List[int]]): Список точек [[x1,y1], [x2,y2], ...]
        color (str): Цвет в HEX формате (#RRGGBBAA)
        camera_id (int): ID камеры
        settings (ROISettings): Настройки детекции
    """
    id: int
    name: str
    points: List[List[int]]
    color: str = "#29B3A85A"
    camera_id: int = 0
    options: ROISettings | None = Field(default_factory=ROISettings)

    @classmethod
    @field_validator('points')
    def validate_points(cls, v):
        if len(v) < 3:
            raise ValueError("ROI must have at least 3 points")
        return v

    @classmethod
    @field_validator('color')
    def validate_color(cls, v):
        if not v.startswith("#") or len(v) not in (7, 9):
            raise ValueError("Color must be in HEX format (#RRGGBB or #RRGGBBAA)")
        return v

    def get_mask(self, width: int, height: int) -> np.ndarray:
        """Генерация маски для ROI"""
        mask = np.zeros((height, width), dtype=np.uint8)
        pts = np.array(self.points, np.int32).reshape((-1, 1, 2))
        cv2.fillPoly(mask, [pts], 255)
        return mask

    @property
    def bgr_color(self) -> tuple:
        """Конвертация HEX цвета в BGR"""
        hex_color = self.color.lstrip("#")
        rgba = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4, 6))
        return (rgba[2], rgba[1], rgba[0])


class ROIEvent(BaseModel):
    event: ROIEventType
    camera: "CameraModelWithRelations"
    timestamp: datetime
    frame: np.ndarray
    original: np.ndarray
    model_config = ConfigDict(arbitrary_types_allowed=True)


class ROIDetectionEvent(ROIEvent):
    roi: ROI
    changes: list[dict]


class ROIRecordEvent(ROIEvent):
    rois: list[ROI] | None = None
    duration: float | None = None
