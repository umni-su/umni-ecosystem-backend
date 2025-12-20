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
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from models.enums.log_code import LogCode
from models.pagination_model import PageParams


class LogPageParams(PageParams):
    entity_id: int | None = Field(default=None)
    start: datetime | None = Field(default=None)
    end: datetime | None = Field(default=None)
    code: LogCode | None = Field(default=None)
    level: str | None = Field(default=None)
    logger_type: str | None = Field(default=None)


class LogEntityCode(BaseModel):
    id: int = Field(...)
    code: LogCode = Field(...)


class LogModel(BaseModel):
    entity_id: int | None = Field(default=None)
    code: int | None = Field(default=None)
    timestamp: datetime | None = Field(default=None)
    level: str | None = Field(default=None)
    logger_type: str | None = Field(default=None)
    message: str | None = Field(default=None)
    details: Optional[Dict[str, Any]] = Field(default_factory=dict())
