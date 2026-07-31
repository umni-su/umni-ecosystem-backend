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
import os
import uuid
from urllib.parse import quote

import httpx
from nio import RoomSendResponse, JoinResponse, RoomSendError, AsyncClient, AsyncClientConfig
from pydantic import Field

from classes.crypto.crypto import Crypto
from classes.l10n.l10n import _
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from classes.notifications.base_registered_notification import BaseRegisteredNotification
from models.notification_model import NotificationOptionsBaseModel, NotificationModel
from models.notification_queue_model import NotificationQueueModel


class MatrixOptionsModel(NotificationOptionsBaseModel):
    """Модель опций для Matrix уведомлений"""
    model_description = _("Matrix configuration")

    homeserver_url: str = Field(
        ...,
        description=_("Matrix homeserver URL (e.g., https://matrix-client.matrix.org)")
    )
    room_id: str = Field(
        ...,
        description=_("Room ID to send messages to (e.g., !abc123:matrix.org)")
    )
    access_token: str = Field(
        ...,
        json_schema_extra={"sensitive": True, "sensitive_type": "token"},
        description=_("Matrix access token for authentication")
    )
    enable_html: bool = Field(
        default=True,
        description=_("Enable HTML formatting in messages")
    )

    @property
    def decrypted_token(self):
        """Возвращает дешифрованный токен"""
        return self.get_decrypted(self.access_token) if self.access_token else None

    def model_post_init(self, __context):
        if self.access_token and not self.access_token.startswith('gAAAAA'):
            self.access_token = Crypto.encrypt(self.access_token)


class MatrixNotification(BaseRegisteredNotification):
    """Обработчик уведомлений через Matrix с поддержкой шифрования (E2EE)"""

    type_id = 3
    name = "matrix"
    description = _("Send notifications via Matrix chat protocol")
    options_model = MatrixOptionsModel

    async def send(
            self,
            notification: 'NotificationModel',
            notification_queue: 'NotificationQueueModel',
            **kwargs
    ) -> bool:
        """Отправляет сообщение в зашифрованную или обычную комнату Matrix"""
        client = None
        try:
            options = self.options_model(**notification.options)

            homeserver = options.homeserver_url.strip().rstrip("/")
            room_id = options.room_id.strip()

            # Для E2EE боту нужен ID (например, @bot:domain.ru). Извлекаем его из токена или опций.
            # Если в options.bot_user_id нет точного ID, matrix-nio может выдать ошибку.
            # Предполагаем, что у вас в options есть user_id бота, либо используем заглушку.
            bot_user_id = getattr(options, 'bot_user_id', "@bot_placeholder:matrix.org").strip()

            # Настройка клиента с включенным шифрованием
            config = AsyncClientConfig(
                encryption_enabled=True,

            )

            # Важно: Для сохранения ключей шифрования между перезапусками
            # желательно указывать store_path (папку для базы данных SQLite)
            store_path = os.path.join(os.getcwd(), ".matrix_store")

            client = AsyncClient(
                homeserver=homeserver,
                user=bot_user_id,
                config=config,
                store_path=store_path
            )

            # Авторизуемся по вашему Bearer-токену
            client.access_token = options.decrypted_token.strip()

            # Формируем контент сообщения
            content = {"msgtype": "m.text", "body": notification_queue.message}

            if options.enable_html:
                plain_body = f"{notification_queue.subject}\n{notification_queue.message}" if notification_queue.subject else notification_queue.message
                formatted = f"<strong>{notification_queue.subject}</strong><br/>{notification_queue.message}" if notification_queue.subject else notification_queue.message
                content.update({
                    "body": plain_body,
                    "format": "org.matrix.custom.html",
                    "formatted_body": formatted
                })
            elif notification_queue.subject:
                content["body"] = f"{notification_queue.subject}\n{notification_queue.message}"

            # 1. Пробуем отправить сообщение
            response = await client.room_send(
                room_id=room_id,
                message_type="m.room.message",
                content=content
            )

            # 2. Если получили ошибку членства (M_FORBIDDEN), пробуем войти
            if isinstance(response, RoomSendError) and response.status_code == "M_FORBIDDEN":
                Logger.info(f"Bot is not in room {room_id}. Attempting to join...", LoggerType.NOTIFICATIONS)

                join_response = await client.join(room_id)
                if isinstance(join_response, JoinResponse):
                    Logger.info(f"Matrix bot successfully joined room {room_id}", LoggerType.NOTIFICATIONS)

                    # Повторяем отправку после успешного входа
                    response = await client.room_send(
                        room_id=room_id,
                        message_type="m.room.message",
                        content=content,
                        ignore_unverified_devices=True
                    )
                else:
                    Logger.err(f"Matrix Join failed: {join_response.message}", LoggerType.NOTIFICATIONS)
                    return False

            # 3. Проверяем финальный статус отправки
            if isinstance(response, RoomSendResponse):
                Logger.info(f"Matrix notification sent to room {room_id}", LoggerType.NOTIFICATIONS)
                return True

            Logger.err(f"Matrix API error: {response.message}", LoggerType.NOTIFICATIONS)
            return False

        except Exception as e:
            Logger.err(f"Matrix notification error: {e}", LoggerType.NOTIFICATIONS)
            return False

        finally:
            if client:
                await client.close()
