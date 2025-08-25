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

from pydantic import BaseModel, Field, field_validator


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
