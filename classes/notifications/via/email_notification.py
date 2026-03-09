# Copyright (C) 2026 Mikhail Sazanov
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

from typing import Dict, Any, Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from pydantic import Field
from classes.crypto.crypto import Crypto
from classes.l10n.l10n import _
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from classes.notifications.base_registered_notification import BaseRegisteredNotification
from models.notification_model import NotificationModel, NotificationOptionsBaseModel
from models.notification_queue_model import NotificationQueueModel
from entities.enums.notification_type_enum import NotificationTypeEnum
from entities.enums.encryption_enum import EncryptionEnum


class EmailOptionsModel(NotificationOptionsBaseModel):
    """Модель опций для Email уведомлений"""
    model_description = _("SMTP Email Configuration")

    host: Optional[str] = Field(
        ...,
        description=_("SMTP host server")
    )
    port: Optional[int] = Field(
        default=587,
        description=_("SMTP port number")
    )
    encryption: Optional[EncryptionEnum] = Field(
        default=None,
        description=_("Encryption type"),
        json_schema_extra={
            "enum": ["ssl", "tls", "startls"]  # <- ui hack
        }
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

    @property
    def decrypted_password(self):
        """Возвращает дешифрованный пароль"""
        return self.get_decrypted(self.password) if self.password else None

    def model_post_init(self, __context):
        if self.password and not self.password.startswith('gAAAAA'):
            self.password = Crypto.encrypt(self.password)


class EmailNotification(BaseRegisteredNotification):
    """Обработчик уведомлений через Email/SMTP"""

    type_id = NotificationTypeEnum.EMAIL.value  # 2
    name = "email"
    description = _("Send notifications via SMTP email")
    options_model = EmailOptionsModel

    async def send(
            self,
            notification: NotificationModel,
            notification_queue: NotificationQueueModel,
            **kwargs
    ) -> bool:
        try:
            options = self.options_model(**notification.options)

            # Создаем сообщение
            msg = MIMEMultipart()
            msg['From'] = formataddr((options.from_name, options.username)) or options.username
            msg['To'] = notification_queue.to
            msg['Subject'] = notification_queue.subject

            # Добавляем текст сообщения
            msg.attach(MIMEText(notification_queue.message, 'plain'))

            # Настраиваем соединение
            if options.encryption and options.encryption.upper() == 'SSL':
                server = smtplib.SMTP_SSL(options.host, options.port)
            else:
                server = smtplib.SMTP(options.host, options.port)
                if options.encryption and options.encryption.upper() == 'TLS':
                    server.starttls()

            # Аутентификация если есть учетные данные
            if options.username and options.decrypted_password:
                server.login(options.username, options.decrypted_password)

            # Отправка сообщения
            server.send_message(msg)
            server.quit()

            return True

        except Exception as e:
            Logger.err(f"Email notification error: {e}", LoggerType.NOTIFICATIONS)
            return False
