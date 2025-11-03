# Copyright (C) 2025 Mikhail Sazanov
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class PluginModel(BaseModel):
    id: Optional[int] = None
    name: str
    display_name: str
    version: str
    description: Optional[str] = None
    active: bool
    author: Optional[str] = None
    url: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    status: str
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class PluginConfigModel(BaseModel):
    """Модель для конфигурационного файла плагина"""
    author: str = Field(None)
    url: Optional[str] = Field(None)
    name: str = Field(None)
    display_name: str = Field(None)
    version: str = Field(None)
    description: Optional[str] = Field(None)
