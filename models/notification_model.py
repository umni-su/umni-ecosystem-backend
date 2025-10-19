# notification_model.py
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

from pydantic import BaseModel, Field
from typing import Optional, Union
from entities.enums.encryption_enum import EncryptionEnum
from entities.enums.notification_type_enum import NotificationTypeEnum


class NotificationOptionsBaseModel(BaseModel):
    """Базовая модель опций уведомления"""
    pass


class NotificationTelegramModel(NotificationOptionsBaseModel):
    """Модель опций для Telegram уведомлений"""
    bot_name: str = Field(..., description="Имя бота")
    bot_token: str = Field(..., description="Токен бота Telegram")


class NotificationEmailSmtpModel(NotificationOptionsBaseModel):
    """Модель опций для Email уведомлений"""
    host: str = Field(..., description="SMTP хост")
    port: int = Field(default=587, description="SMTP порт")
    encryption: Optional[EncryptionEnum] = Field(default=None, description="Тип шифрования")
    username: Optional[str] = Field(default=None, description="Имя пользователя")
    password: Optional[str] = Field(default=None, description="Пароль")
    from_name: Optional[str] = Field(default=None, description="Имя отправителя")


class NotificationCreateModel(BaseModel):
    """Модель для создания уведомления"""
    name: str = Field(..., description="Название уведомления")
    to: str = Field(..., description="Получатель (chat_id для Telegram, email для почты)")
    type: NotificationTypeEnum = Field(..., description="Тип уведомления")
    active: bool = Field(default=True, description="Активно ли уведомление")
    options: Union[NotificationTelegramModel, NotificationEmailSmtpModel] = Field(
        ...,
        description="Настройки уведомления"
    )


class NotificationModel(BaseModel):
    """Полная модель уведомления"""
    id: int = Field(..., description="ID уведомления")
    name: str = Field(..., description="Название уведомления")
    to: str = Field(..., description="Получатель")
    type: NotificationTypeEnum = Field(..., description="Тип уведомления")
    active: bool = Field(..., description="Активно ли уведомление")
    options: Union[NotificationTelegramModel, NotificationEmailSmtpModel] = Field(
        ...,
        description="Настройки уведомления"
    )

    class Config:
        from_attributes = True


class NotificationUpdateModel(BaseModel):
    """Модель для обновления уведомления"""
    name: Optional[str] = Field(None, description="Название уведомления")
    to: Optional[str] = Field(None, description="Получатель")
    type: Optional[NotificationTypeEnum] = Field(None, description="Тип уведомления")
    active: Optional[bool] = Field(None, description="Активно ли уведомление")
    options: Optional[Union[NotificationTelegramModel, NotificationEmailSmtpModel]] = Field(
        None,
        description="Настройки уведомления"
    )
