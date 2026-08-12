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

import asyncio
import hashlib
import os
from pathlib import Path
from typing import Dict, Any, Optional

from pydantic import Field
from telethon import TelegramClient, Button, connection
from telethon.network.connection.tcpmtproxy import (
    ConnectionTcpMTProxyAbridged,
    ConnectionTcpMTProxyIntermediate,
    ConnectionTcpMTProxyRandomizedIntermediate,
)

from classes.crypto.crypto import Crypto
from classes.l10n.l10n import _
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from classes.notifications.base_registered_notification import BaseRegisteredNotification
from models.notification_model import NotificationModel, NotificationOptionsBaseModel
from models.notification_queue_model import NotificationQueueModel
from entities.enums.notification_type_enum import NotificationTypeEnum
from entities.enums.telegram_proxy_type_enum import TelegramProxyTypeEnum
from entities.enums.telegram_mtproxy_connection_enum import TelegramMTProxyConnectionEnum


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
    api_id: Optional[int] = Field(
        None,
        description=_("Telegram API ID (https://my.telegram.org -> API development tools)")
    )
    api_hash: Optional[str] = Field(
        None,
        json_schema_extra={
            "sensitive": True,
            "sensitive_type": "password"
        },
        description=_("Telegram API hash (https://my.telegram.org -> API development tools)")
    )
    proxy_type: TelegramProxyTypeEnum = Field(
        TelegramProxyTypeEnum.OFF,
        description=_("Proxy type used to reach Telegram (MTProxy or SOCKS5)")
    )
    proxy_host: Optional[str] = Field(
        None,
        description=_("Proxy host")
    )
    proxy_port: Optional[int] = Field(
        None,
        description=_("Proxy port")
    )
    proxy_secret: Optional[str] = Field(
        None,
        json_schema_extra={
            "sensitive": True,
            "sensitive_type": "password"
        },
        description=_("MTProxy secret (32 hex chars, or 32 zeros if the proxy has no secret)")
    )
    proxy_username: Optional[str] = Field(
        None,
        json_schema_extra={
            "sensitive": True,
            "sensitive_type": "password"
        },
        description=_("Proxy username (SOCKS5 auth)")
    )
    proxy_password: Optional[str] = Field(
        None,
        json_schema_extra={
            "sensitive": True,
            "sensitive_type": "password"
        },
        description=_("Proxy password (SOCKS5 auth)")
    )
    connection_type: TelegramMTProxyConnectionEnum = Field(
        TelegramMTProxyConnectionEnum.RANDOMIZED_INTERMEDIATE,
        description=_("MTProxy connection protocol (RandomizedIntermediate is preferred)")
    )

    @property
    def decrypted_bot_token(self) -> Optional[str]:
        """Возвращает дешифрованный токен для использования в коде"""
        return self.get_decrypted(self.bot_token) if self.bot_token else None

    @property
    def decrypted_api_hash(self) -> Optional[str]:
        """Возвращает дешифрованный api_hash для использования в коде"""
        return self.get_decrypted(self.api_hash) if self.api_hash else None

    @property
    def decrypted_proxy_secret(self) -> Optional[str]:
        """Возвращает дешифрованный secret MTProxy для использования в коде"""
        return self.get_decrypted(self.proxy_secret) if self.proxy_secret else None

    @property
    def decrypted_proxy_password(self) -> Optional[str]:
        """Возвращает дешифрованный пароль прокси для использования в коде"""
        return self.get_decrypted(self.proxy_password) if self.proxy_password else None

    def model_post_init(self, __context):
        for field_name in ('bot_token', 'api_hash', 'proxy_secret', 'proxy_password'):
            value = getattr(self, field_name, None)
            if value and not value.startswith('gAAAAA'):
                setattr(self, field_name, Crypto.encrypt(value))


class TelegramNotification(BaseRegisteredNotification):
    """Обработчик уведомлений через Telegram (MTProto + MTProxy/SOCKS5)"""

    type_id = NotificationTypeEnum.TELEGRAM.value  # 1
    name = "telegram"
    description = _("Send notifications via Telegram bot")
    options_model = TelegramOptionsModel

    _connection_map = {
        TelegramMTProxyConnectionEnum.ABRIDGED: ConnectionTcpMTProxyAbridged,
        TelegramMTProxyConnectionEnum.INTERMEDIATE: ConnectionTcpMTProxyIntermediate,
        TelegramMTProxyConnectionEnum.RANDOMIZED_INTERMEDIATE: ConnectionTcpMTProxyRandomizedIntermediate,
    }

    # ------------------------------------------------------------------
    # Вспомогательные методы
    # ------------------------------------------------------------------

    @staticmethod
    def _session_dir() -> str:
        """Каталог для session-файлов Telethon"""
        session_dir = Path(__file__).resolve().parents[3] / 'storage' / 'sessions'
        os.makedirs(session_dir, exist_ok=True)
        return str(session_dir)

    @staticmethod
    def _session_path(bot_token: str) -> str:
        """Путь к session-файлу для конкретного бота"""
        digest = hashlib.sha256(bot_token.encode('utf-8')).hexdigest()[:16]
        return os.path.join(TelegramNotification._session_dir(), f"telegram_{digest}.session")

    @staticmethod
    def _proxy_kwargs(options: 'TelegramOptionsModel') -> Dict[str, Any]:
        """Строит proxy/connection kwargs для TelegramClient"""
        if options.proxy_type == TelegramProxyTypeEnum.OFF:
            return {}

        host = options.proxy_host
        port = options.proxy_port
        if not host or not port:
            raise ValueError(_("Proxy host and port are required when proxy is enabled"))

        if options.proxy_type == TelegramProxyTypeEnum.MTPROXY:
            secret = options.decrypted_proxy_secret or ('0' * 32)
            return {
                'connection': TelegramNotification._connection_map[options.connection_type],
                'proxy': (host, int(port), secret),
            }

        # SOCKS5
        proxy = {
            'proxy_type': 'socks5',
            'addr': host,
            'port': int(port),
            'rdns': True,
        }
        if options.proxy_username:
            proxy['username'] = options.proxy_username
            proxy['password'] = options.decrypted_proxy_password or ''
        return {'proxy': proxy}

    def _build_client(self, options: 'TelegramOptionsModel') -> TelegramClient:
        """Создает TelegramClient для отправки (клиент создается на каждый вызов)"""

        api_id = options.api_id
        api_hash = options.decrypted_api_hash
        if not api_id or not api_hash:
            raise ValueError(_("Telegram API ID and API hash are required"))
        bot_token = options.decrypted_bot_token or ''
        return TelegramClient(
            self._session_path(bot_token),
            api_id,
            api_hash,
            device_model='UMNI Ecosystem',
            app_version='1.0',
            system_version='Windows',
            **self._proxy_kwargs(options),
        )

    @staticmethod
    def _run_in_new_loop(coro) -> Any:
        """Запускает корутину в отдельном (новом) event loop.

        Используется из синхронного контекста (validate_config).
        Если уже находимся внутри работающего event loop - живая проверка
        пропускается (нельзя создать вложенный loop в том же потоке).
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        Logger.warn("Telegram live config check skipped: running inside an event loop", LoggerType.NOTIFICATIONS)
        return True

    @staticmethod
    async def _disconnect_safe(client: Optional[TelegramClient]):
        if client is not None:
            try:
                await client.disconnect()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Основные методы
    # ------------------------------------------------------------------

    def _format_message(self, notification_queue: NotificationQueueModel) -> str:
        text = (notification_queue.subject or '')
        return f"<b>{text}</b>\r\n{notification_queue.message}"

    async def send(
            self,
            notification: NotificationModel,
            notification_queue: NotificationQueueModel,
            **kwargs
    ) -> bool:
        client = None
        try:
            # Получаем опции из notification.options
            options = self.options_model(**notification.options)

            bot_token = options.decrypted_bot_token
            if not bot_token:
                raise ValueError(_("Bot token is required"))

            # Получаем chat_id из параметра 'to'
            chat_id = int(notification_queue.to)

            # Создаем и подключаем клиент (MTProto)
            client = self._build_client(options)
            await client.start(bot_token=bot_token)

            # Параметры форматирования
            parse_mode = kwargs.get('parse_mode', 'html')
            disable_web_page_preview = kwargs.get('disable_web_page_preview', True)

            text = self._format_message(notification_queue)

            # Отправляем сообщение
            await client.send_message(
                chat_id,
                text,
                parse_mode=parse_mode,
                link_preview=not disable_web_page_preview,
            )

            return True

        except Exception as e:
            Logger.err(f"Telegram notification error: {e}", LoggerType.NOTIFICATIONS)
            return False

        finally:
            await self._disconnect_safe(client)

    def validate_config(self, options: Dict[str, Any]) -> bool:
        """Дополнительная валидация с живой проверкой токена"""
        if not super().validate_config(options):
            return False

        try:
            model = self.options_model(**options)

            if not model.decrypted_bot_token or not model.api_id or not model.decrypted_api_hash:
                return False

            # Живая проверка: подключаемся к Telegram (через прокси, если задан)
            return bool(self._run_in_new_loop(self._check_bot(model)))

        except Exception as e:
            Logger.err(f"Telegram validate_config error: {e}", LoggerType.NOTIFICATIONS)
            return False

    async def _check_bot(self, options: 'TelegramOptionsModel') -> bool:
        """Подключается к Telegram и проверяет валидность бота"""
        client = None
        try:
            client = self._build_client(options)
            await client.start(bot_token=options.decrypted_bot_token)
            me = await client.get_me()
            return me is not None
        finally:
            await self._disconnect_safe(client)

    async def send_with_buttons(self, notification: NotificationModel, message: str,
                                buttons: Dict[str, str], **kwargs) -> bool:
        """Отправляет сообщение с кнопками. buttons: {label: url}"""
        client = None
        try:
            options = self.options_model(**notification.options)

            bot_token = options.decrypted_bot_token
            if not bot_token:
                raise ValueError(_("Bot token is required"))

            chat_id = int(kwargs.get('to'))
            if not chat_id:
                raise ValueError(_("Recipient (to) is required"))

            client = self._build_client(options)
            await client.start(bot_token=bot_token)

            rows = [[Button.url(label, url) for label, url in buttons.items()]]
            await client.send_message(chat_id, message, buttons=rows)

            return True

        except Exception as e:
            Logger.err(f"Telegram notification error: {e}", LoggerType.NOTIFICATIONS)
            return False

        finally:
            await self._disconnect_safe(client)
