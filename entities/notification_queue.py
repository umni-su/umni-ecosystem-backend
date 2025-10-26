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
from typing import Optional, Dict, Any

from sqlmodel import Field, JSON

from entities.mixins.created_updated import TimeStampMixin
from entities.mixins.id_column import IdColumnMixin


class NotificationQueueEntityBase:
    """Базовая сущность для очереди уведомлений"""
    notification_id: int = Field(
        nullable=False,
        index=True,
        description="ID уведомления из таблицы notifications"
    )
    to: Optional[str] = Field(
        default=None,
        nullable=True,
    )
    subject: Optional[str] = Field(
        default=None,
        nullable=True,
    )
    message: str = Field(
        nullable=False
    )
    priority: int = Field(
        default=0,
        nullable=False,
        description="Priority (0 - low, 1 - medium, 2 - high)"
    )
    retry_count: int = Field(
        default=0,
        nullable=False,
    )
    max_retries: int = Field(
        default=3,
        nullable=False,
    )
    last_attempt: Optional[datetime] = Field(
        default=None,
        nullable=True
    )
    options: Optional[Dict[str, Any]] = Field(
        sa_type=JSON,
        default=None,
        nullable=True,
    )


class NotificationQueueEntity(
    TimeStampMixin,
    NotificationQueueEntityBase,
    IdColumnMixin,
    table=True
):
    __tablename__ = 'notifications_queue'
