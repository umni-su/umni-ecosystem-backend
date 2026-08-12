#  Copyright (C) 2026 Mikhail Sazanov
#  #
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

from typing import Any, Optional

from pydantic import BaseModel


class WidgetControl(BaseModel):
    """Элемент управления составного виджета (привязан к сенсору по роли)."""

    role: str
    sensor_id: Optional[int] = None
    sensor_type: Optional[int] = None
    capability: Optional[str] = None
    identifier: Optional[str] = None
    name: Optional[str] = None
    value: Any = None
    unit: Optional[str] = None
    writable: bool = False
    readonly: bool = False
    min: Optional[float] = None
    max: Optional[float] = None
    values: Optional[list] = None
    options: Optional[dict] = None


class WidgetDescriptor(BaseModel):
    """Составной виджет устройства: тип + элементы управления."""

    type: Optional[str] = None
    name: Optional[str] = None
    controls: list[WidgetControl] = []
