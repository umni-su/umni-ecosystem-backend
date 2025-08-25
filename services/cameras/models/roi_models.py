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

import datetime

import cv2
from typing import List
import numpy as np
from pydantic import BaseModel, field_validator, Field, ConfigDict
from services.cameras.enums.roi_enum import ROIEventType
from models.camera_model import CameraModelWithRelations
from services.cameras.models.roi_settings import ROISettings


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
