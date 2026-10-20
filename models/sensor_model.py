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

from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel, computed_field

from models.sensor_history_model import SensorHistoryModel
from classes.devices.device_sensor_type_enum import DeviceSensorTypeEnum

from models.device_model import DeviceModelMain


class SensorCreateModel(BaseModel):
    device_id: int
    type: DeviceSensorTypeEnum
    capability: str
    identifier: str
    active: bool
    role: Optional[str] = None
    name: Optional[str] = None
    visible_name: Optional[str] = None
    options: Optional[dict] = None
    value: Optional[str] = None
    photo: Optional[str] = None
    last_sync: Optional[datetime] = None
    unit: Optional[str] = None
    icon: Optional[str] = None

    class Config:
        extra = 'ignore'


class SensorModel(SensorCreateModel):
    id: int | None = None

    # ---------- Зависимые поля типа сенсора (тянутся из DeviceSensorTypeEnum) ----------

    @property
    def type_enum(self) -> Optional[DeviceSensorTypeEnum]:
        """Enum типа сенсора (None, если тип неизвестен/не задан)."""
        if self.type is None:
            return None
        try:
            return DeviceSensorTypeEnum(self.type)
        except ValueError:
            return None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def writable(self) -> bool:
        """Поддерживает ли сенсор запись. Источник правды — DeviceSensorTypeEnum."""
        stype = self.type_enum
        return stype.writable if stype else False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def type_name(self) -> Optional[str]:
        """Имя enum-члена (SWITCH, SETPOINT, ...)."""
        stype = self.type_enum
        return stype.name if stype else None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def type_label(self) -> Optional[str]:
        """Локализованное название типа."""
        stype = self.type_enum
        return stype.label if stype else None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def ui_component(self) -> Optional[str]:
        """UI-компонент типа (switch, setpoint, number, ...)."""
        stype = self.type_enum
        return stype.ui_component if stype else None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def type_icon(self) -> Optional[str]:
        """Иконка типа (mdi-...)."""
        stype = self.type_enum
        return stype.icon if stype else None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def default_role(self) -> Optional[str]:
        """Роль по умолчанию из типа (None у generic-типов)."""
        stype = self.type_enum
        return stype.default_role if stype else None


class SensorUpdateModel(SensorModel):
    pass


class SensorUpdateModelUi(BaseModel):
    id: int | None = None
    visible_name: Optional[str] = None
    photo: Optional[str] = None


class SensorModelWithHistory(SensorModel):
    history: list[SensorHistoryModel]


class SensorModelWithDevice(SensorModel):
    device: DeviceModelMain = None


class SensorPayload(BaseModel):
    value: Optional[Union[int | float | str | bool]]
