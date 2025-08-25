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
