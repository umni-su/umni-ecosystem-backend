from pydantic import BaseModel

from entities.enums.encryption_enum import EncryptionEnum
from entities.enums.notification_type_enum import NotificationTypeEnum


class NotificationOptionsBaseModel(BaseModel):
    pass


class NotificationTelegramModel(NotificationOptionsBaseModel):
    bot_name: str
    bot_token: str


class NotificationEmailSmtpModel(NotificationOptionsBaseModel):
    host: str
    port: int = 587
    encryption: EncryptionEnum | None = None
    username: str | None = None
    password: str | None = None
    from_name: str | None = None


class NotificationModel(BaseModel):
    id: int
    name: str
    to: str
    type: NotificationTypeEnum
    options: NotificationOptionsBaseModel
