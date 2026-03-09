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
import telebot
from pydantic import Field
from classes.crypto.crypto import Crypto
from classes.l10n.l10n import _
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from classes.notifications.base_registered_notification import BaseRegisteredNotification
from models.notification_model import NotificationModel, NotificationOptionsBaseModel
from models.notification_queue_model import NotificationQueueModel
from entities.enums.notification_type_enum import NotificationTypeEnum


class TelegramOptionsModel(NotificationOptionsBaseModel):
    """Модель опций для Telegram уведомлений"""
    model_description = _("Telegram Configuration")

    bot_name: Optional[str] = Field(..., description=_("Bot name"))
    bot_token: Optional[str] = Field(
        ...,
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


class TelegramNotification(BaseRegisteredNotification):
    """Обработчик уведомлений через Telegram"""

    type_id = NotificationTypeEnum.TELEGRAM.value  # 1
    name = "telegram"
    description = _("Send notifications via Telegram bot")
    options_model = TelegramOptionsModel

    def __init__(self):
        super().__init__()
        self._bot_cache = {}  # Кэш для экземпляров бота

    def _get_bot_instance(self, bot_token: str) -> telebot.TeleBot:
        """Получает или создает экземпляр бота для токена"""
        if bot_token not in self._bot_cache:
            self._bot_cache[bot_token] = telebot.TeleBot(bot_token)
        return self._bot_cache[bot_token]

    def _format_message(self, notification_queue: NotificationQueueModel) -> str:
        text = (notification_queue.subject or '')
        return f"<b>{text}</b>\r\n{notification_queue.message}"

    async def send(
            self,
            notification: NotificationModel,
            notification_queue: NotificationQueueModel,
            **kwargs
    ) -> bool:
        try:
            # Получаем опции из notification.options
            options = self.options_model(**notification.options)

            # Получаем chat_id из параметра 'to'
            chat_id = int(notification_queue.to)

            # Получаем экземпляр бота
            bot = self._get_bot_instance(options.decrypted_bot_token)

            # Параметры форматирования
            parse_mode = kwargs.get('parse_mode', 'HTML')
            disable_web_page_preview = kwargs.get('disable_web_page_preview', True)

            text = self._format_message(notification_queue)

            # Отправляем сообщение
            sent_message = bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview
            )

            return sent_message is not None

        except Exception as e:
            Logger.err(f"Telegram notification error: {e}", LoggerType.NOTIFICATIONS)
            return False

    def validate_config(self, options: Dict[str, Any]) -> bool:
        """Дополнительная валидация с проверкой токена"""
        if not super().validate_config(options):
            return False

        try:
            # Проверяем токен
            model = self.options_model(**options)
            bot = telebot.TeleBot(model.decrypted_bot_token)
            bot_info = bot.get_me()
            return bot_info is not None
        except Exception:
            return False

    # Дополнительные методы для Telegram
    def send_with_buttons(self, notification: NotificationModel, message: str,
                          buttons: Dict[str, str], **kwargs) -> bool:
        """Отправляет сообщение с кнопками"""
        # Реализация...
        pass
