# telegram_notification_handler.py
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

import telebot
from typing import Any, Dict
from classes.l10n.l10n import _
from fastapi import HTTPException
from classes.crypto.crypto import Crypto
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from classes.notifications.notification_handler import NotificationHandler
from models.notification_model import NotificationModel, NotificationTelegramModel
from models.notification_queue_model import NotificationQueueModel


class TelegramNotificationHandler(NotificationHandler):
    """Обработчик уведомлений через Telegram с использованием pyTelegramBotAPI"""

    def __init__(self):
        self._bot_cache = {}  # Кэш для экземпляров бота

    def _get_bot_instance(self, bot_token: str) -> telebot.TeleBot:
        """Получает или создает экземпляр бота для токена"""
        if bot_token not in self._bot_cache:
            self._bot_cache[bot_token] = telebot.TeleBot(bot_token)
        return self._bot_cache[bot_token]

    async def send(
            self,
            notification: NotificationModel,
            notification_queue: NotificationQueueModel,
            **kwargs
    ) -> bool:
        """
        Отправляет уведомление через Telegram

        Returns:
            bool: True если отправка успешна, False в случае ошибки
        """
        try:
            options = NotificationTelegramModel(**notification.options.model_dump())

            # Получаем chat_id из параметра 'to'
            chat_id = int(notification_queue.to)

            # Получаем экземпляр бота
            bot = self._get_bot_instance(options.decrypted_bot_token)

            # Параметры форматирования
            parse_mode = kwargs.get('parse_mode', 'HTML')
            disable_web_page_preview = kwargs.get('disable_web_page_preview', True)

            # Отправляем сообщение
            sent_message = bot.send_message(
                chat_id=chat_id,
                text=notification_queue.message,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview
            )

            # Если нужно отправить с клавиатурой
            reply_markup = kwargs.get('reply_markup')
            if reply_markup:
                sent_message = bot.send_message(
                    chat_id=chat_id,
                    text=notification_queue.message,
                    parse_mode=parse_mode,
                    disable_web_page_preview=disable_web_page_preview,
                    reply_markup=reply_markup
                )

            return sent_message is not None

        except telebot.apihelper.ApiTelegramException as e:
            print(f"Telegram API error: {e}")
            return False
        except Exception as e:
            print(f"Telegram notification error: {e}")
            return False

    def validate_config(self, options: Dict[str, Any]) -> bool:
        """
        Проверяет корректность конфигурации Telegram уведомления

        Args:
            options: Настройки уведомления

        Returns:
            bool: True если конфигурация валидна
        """
        try:
            telegram_options = NotificationTelegramModel(**options)

            # Проверяем наличие обязательных полей
            if not all([
                telegram_options.bot_token,
                telegram_options.bot_name
            ]):
                return False

            # Дополнительная проверка токена (можно сделать тестовый запрос)
            return self._test_bot_token(telegram_options.bot_token)

        except Exception as e:
            print(f"Telegram config validation error: {e}")
            return False

    def _decrypt_token(self, token):
        if token.startswith('gAAAAA'):
            return Crypto.decrypt(token)
        return token

    def _test_bot_token(self, bot_token: str) -> bool:
        """
        Проверяет валидность токена бота

        Args:
            bot_token: Токен бота Telegram

        Returns:
            bool: True если токен валиден
        """
        try:
            bot = telebot.TeleBot(self._decrypt_token(bot_token))
            bot_info = bot.get_me()
            return bot_info is not None
        except Exception as e:
            Logger.err(e, LoggerType.NOTIFICATIONS)
            raise HTTPException(
                status_code=419,
                detail=_("Notification not found")
            )

    def send_with_buttons(self, notification: NotificationModel, message: str,
                          buttons: Dict[str, str], **kwargs) -> bool:
        """
        Отправляет сообщение с кнопками

        Args:
            notification: Модель уведомления
            message: Текст сообщения
            buttons: Словарь {текст_кнопки: callback_data}
            **kwargs: Дополнительные параметры

        Returns:
            bool: Результат отправки
        """
        try:
            options = NotificationTelegramModel(**notification.options.model_dump())
            bot = self._get_bot_instance(options.decrypted_bot_token)
            chat_id = notification.to

            # Создаем inline клавиатуру
            markup = telebot.types.InlineKeyboardMarkup()
            for text, callback_data in buttons.items():
                markup.add(telebot.types.InlineKeyboardButton(
                    text=text,
                    callback_data=callback_data
                ))

            sent_message = bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=kwargs.get('parse_mode', 'HTML'),
                reply_markup=markup
            )

            return sent_message is not None

        except Exception as e:
            print(f"Telegram buttons error: {e}")
            return False

    def send_photo(self, notification: NotificationModel, photo_path: str,
                   caption: str = "", **kwargs) -> bool:
        """
        Отправляет фото через Telegram

        Args:
            notification: Модель уведомления
            photo_path: Путь к файлу или file_id
            caption: Подпись к фото
            **kwargs: Дополнительные параметры

        Returns:
            bool: Результат отправки
        """
        try:
            options = NotificationTelegramModel(**notification.options.model_dump())
            bot = self._get_bot_instance(options.decrypted_bot_token)
            chat_id = notification.to

            with open(photo_path, 'rb') as photo:
                sent_message = bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=caption,
                    parse_mode=kwargs.get('parse_mode', 'HTML')
                )

            return sent_message is not None

        except Exception as e:
            print(f"Telegram photo error: {e}")
            return False

    def send_document(self, notification: NotificationModel, document_path: str,
                      caption: str = "", **kwargs) -> bool:
        """
        Отправляет документ через Telegram

        Args:
            notification: Модель уведомления
            document_path: Путь к файлу
            caption: Подпись к документу
            **kwargs: Дополнительные параметры

        Returns:
            bool: Результат отправки
        """
        try:
            options = NotificationTelegramModel(**notification.options.model_dump())
            bot = self._get_bot_instance(options.decrypted_bot_token)
            chat_id = notification.to

            with open(document_path, 'rb') as doc:
                sent_message = bot.send_document(
                    chat_id=chat_id,
                    document=doc,
                    caption=caption,
                    parse_mode=kwargs.get('parse_mode', 'HTML')
                )

            return sent_message is not None

        except Exception as e:
            print(f"Telegram document error: {e}")
            return False
