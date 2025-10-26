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

from pydantic import BaseModel, Field


class NotificationQueueBaseModel(BaseModel):
    """Базовая модель для очереди уведомлений"""
    notification_id: int = Field(..., description="ID уведомления")
    to: Optional[str] = Field(None, description="Получатель")
    subject: Optional[str] = Field(None, description="Тема сообщения")
    message: str = Field(..., description="Текст сообщения")
    priority: int = Field(default=0, description="Приоритет (0-низкий, 1-средний, 2-высокий)")
    max_retries: int = Field(default=3, description="Максимальное количество попыток")
    options: Optional[Dict[str, Any]] = Field(None, description="Дополнительные опции")


class NotificationQueueCreateModel(NotificationQueueBaseModel):
    """Модель для создания элемента очереди"""
    pass


class NotificationQueueModel(NotificationQueueBaseModel):
    """Полная модель элемента очереди"""
    id: int
    retry_count: int = Field(default=0, description="Количество попыток отправки")
    last_attempt: Optional[datetime] = Field(None, description="Время последней попытки")
    created: datetime
    updated: datetime

    class Config:
        from_attributes = True


class NotificationQueueUpdateModel(BaseModel):
    """Модель для обновления элемента очереди"""
    to: Optional[str] = None
    subject: Optional[str] = None
    message: Optional[str] = None
    priority: Optional[int] = None
    retry_count: Optional[int] = None
    max_retries: Optional[int] = None
    last_attempt: Optional[datetime] = None
    options: Optional[Dict[str, Any]] = None
