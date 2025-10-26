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

from pydantic import BaseModel, Field, computed_field
from typing import Optional, Union

from classes.crypto.crypto import Crypto
from classes.l10n.l10n import _
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from classes.ui.ui_form_generator import UIEnhancedModel
from entities.enums.encryption_enum import EncryptionEnum
from entities.enums.notification_type_enum import NotificationTypeEnum


class NotificationOptionsBaseModel(UIEnhancedModel):
    """Базовая модель опций уведомления"""
    model_description = ''

    @classmethod
    def get_decrypted(cls, val: str):
        if val and val.startswith('gAAAAA'):
            try:
                return Crypto.decrypt(val)
            except Exception as e:
                Logger.warn(f"Failed to decrypt value: {e}", LoggerType.NOTIFICATIONS)
                return val
        return val


class NotificationTelegramModel(NotificationOptionsBaseModel):
    """Модель опций для Telegram уведомлений"""
    model_description = _("Telegram Configuration")

    bot_name: str = Field(..., description=_("Bot name"))
    bot_token: str = Field(
        json_schema_extra={
            "sensitive": True,
            "sensitive_type": "token"
        },
        description=_("Bot token")
    )

    @property
    def decrypted_bot_token(self):
        """Возвращает дешифрованный токен для использования в коде"""
        return self.get_decrypted(self.bot_token)

    def model_post_init(self, __context):
        if self.bot_token and not self.bot_token.startswith('gAAAAA'):
            self.bot_token = Crypto.encrypt(self.bot_token)


class NotificationEmailSmtpModel(NotificationOptionsBaseModel):
    """Модель опций для Email уведомлений"""

    model_description = _("SMTP Email Configuration")

    host: str = Field(..., description=_("SMTP host server"))

    port: int = Field(default=587, description=_("SMTP port number"))

    encryption: Optional[EncryptionEnum] = Field(
        default=None,
        description=_("Encryption type")
    )
    username: Optional[str] = Field(
        default=None,
        description=_("Username")
    )
    password: Optional[str] = Field(
        default=None,
        json_schema_extra={
            "sensitive": True,
            "sensitive_type": "password"
        },
        description=_("Password")
    )
    from_name: Optional[str] = Field(
        default=None,
        description=_("Sender name displayed in emails")
    )

    def get_valid_from(self):
        return f"{self.from_name} <{self.username}>"

    def model_post_init(self, __context):
        if not self.password.startswith('gAAAAA'):
            self.password = Crypto.encrypt(self.password)

    @property
    def decrypted_password(self):
        """Возвращает дешифрованный токен для использования в коде"""
        return self.get_decrypted(self.password)


class NotificationCreateModel(BaseModel):
    """Модель для создания уведомления"""
    name: str = Field(..., description=_("Notification name"))
    type: NotificationTypeEnum = Field(..., description=_("Notification type"))
    active: bool = Field(default=True, description=_("Notification is active"))
    options: Union[NotificationTelegramModel, NotificationEmailSmtpModel] = Field(
        ...,
        description=_("Notification settings")
    )


class NotificationModel(BaseModel):
    """Полная модель уведомления"""
    id: int = Field(..., description=_("Notification ID"))
    name: str = Field(..., description=_("Notification name"))
    type: NotificationTypeEnum = Field(..., description=_("Notification type"))
    active: bool = Field(..., description=_("Notification is active"))
    options: Union[NotificationTelegramModel, NotificationEmailSmtpModel] = Field(
        ...,
        description=_("Notification settings")
    )

    @computed_field
    def type_str(self) -> str:
        return self.type.name

    class Config:
        from_attributes = True


class NotificationUpdateModel(BaseModel):
    """Модель для обновления уведомления"""
    name: Optional[str] = Field(None, description=_("Notification name"))
    type: Optional[NotificationTypeEnum] = Field(None, description=_("Notification type"))
    active: Optional[bool] = Field(None, description=_("Notification is active"))
    options: Optional[Union[NotificationTelegramModel, NotificationEmailSmtpModel]] = Field(
        None,
        description=_("Notification settings")
    )
