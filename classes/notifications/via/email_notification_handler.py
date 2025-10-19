# email_notification_handler.py
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

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any, Dict

from classes.notifications.notification_handler import NotificationHandler
from models.notification_model import NotificationModel, NotificationEmailSmtpModel


class EmailNotificationHandler(NotificationHandler):
    """Обработчик уведомлений через Email/SMTP"""

    async def send(self, notification: NotificationModel, message: str, **kwargs) -> bool:
        try:
            options = NotificationEmailSmtpModel(**notification.options)
            subject = kwargs.get('subject', 'Уведомление')

            # Создаем сообщение
            msg = MIMEMultipart()
            msg['From'] = options.from_name or options.username
            msg['To'] = notification.to
            msg['Subject'] = subject

            # Добавляем текст сообщения
            msg.attach(MIMEText(message, 'plain'))

            # Настраиваем соединение
            if options.encryption == 'SSL':
                server = smtplib.SMTP_SSL(options.host, options.port)
            else:
                server = smtplib.SMTP(options.host, options.port)
                if options.encryption == 'TLS':
                    server.starttls()

            # Аутентификация если есть учетные данные
            if options.username and options.password:
                server.login(options.username, options.password)

            # Отправка сообщения
            server.send_message(msg)
            server.quit()

            return True

        except Exception as e:
            print(f"Email notification error: {e}")
            return False

    def validate_config(self, options: Dict[str, Any]) -> bool:
        try:
            email_options = NotificationEmailSmtpModel(**options)
            return all([
                email_options.host,
                email_options.port,
                email_options.from_name
            ])
        except Exception:
            return False
