## Инициализация при старте приложения

```python
# main.py или другой файл инициализации
from classes.notifications.notification_factory import NotificationFactory
from classes.notifications.telegram_notification import TelegramNotification
from classes.notifications.email_notification import EmailNotification


def register_builtin_notifications():
    """Регистрирует встроенные уведомления"""

    # Регистрация через enum (для обратной совместимости)
    NotificationFactory.register_from_enum(
        NotificationTypeEnum.TELEGRAM,
        TelegramNotification
    )

    # Или прямая регистрация
    NotificationFactory.register_notification(EmailNotification)

    # Можно также добавить уведомления с кастомными ID
    # NotificationFactory.register_notification(SomeCustomNotification)


# Вызываем при старте приложения
register_builtin_notifications()
```

## Пример создания плагина разработчиком

```python
# plugins/my_custom_notification/__init__.py
from typing import Dict, Any
from pydantic import Field
from classes.notifications.base_registered_notification import BaseRegisteredNotification
from models.notification_options_base import NotificationOptionsBaseModel
from classes.notifications.notification_factory import NotificationFactory


class CustomOptionsModel(NotificationOptionsBaseModel):
    """Модель опций для кастомного уведомления"""
    model_description = "Custom Notification Configuration"

    api_key: str = Field(
        ...,
        json_schema_extra={"sensitive": True},
        description="API Key for service"
    )
    endpoint: str = Field(..., description="API Endpoint")


class CustomNotification(BaseRegisteredNotification):
    """Кастомное уведомление"""

    type_id = 1001  # Уникальный ID для плагина
    name = "custom_service"
    description = "Send notifications to custom service"
    options_model = CustomOptionsModel

    async def send(
            self,
            notification: NotificationModel,
            notification_queue: NotificationQueueModel,
            **kwargs
    ) -> bool:
        # Реализация отправки
        pass


# Регистрация при загрузке плагина
NotificationFactory.register_notification(CustomNotification)
```

# Касательно интеграции Telegram (MTProto + MTProxy)

Уведомления через Telegram отправляются через **Telethon** (MTProto), поэтому поддерживается работа через **MTProxy** и **SOCKS5** прокси. `pyTelegramBotAPI` (Bot API) больше не используется.

## Настройка формы уведомления (options)

- `bot_name` — имя бота (любое).
- `bot_token` — токен бота от @BotFather (хранится зашифрованным).
- `api_id` / `api_hash` — получить на https://my.telegram.org -> "API development tools".
  Они не секретны, но привязаны к вашему аккаунту разработчика и нужны для MTProto.
- `proxy_type` — `off` / `mtproxy` / `socks5`.
- `proxy_host` / `proxy_port` — адрес и порт прокси.
- `proxy_secret` — секрет MTProxy (32 hex-символа). Если у прокси нет секрета —
  вводить не нужно (используются 32 нуля).
- `proxy_username` / `proxy_password` — авторизация на SOCKS5 (если требуется).
- `connection_type` — протокол MTProxy:
  - `randomized_intermediate` (по умолчанию, рекомендуется),
  - `intermediate`,
  - `abridged`.

## Пример строки для MTProxy

```
mtproxy.example.com:2002  secret=0123456789abcdef0123456789abcdef
```

В форме: `proxy_type=mtproxy`, `proxy_host=mtproxy.example.com`, `proxy_port=2002`,
`proxy_secret=0123456789abcdef0123456789abcdef`.

## Session-файлы

Telethon сохраняет авторизацию в `storage/sessions/telegram_<hash>.session`
(по одному файлу на бота). Каталог игнорируется git. При смене прокси/секрета
для того же бота можно удалить соответствующий `.session`, чтобы пересоздать.

# Касательно интеграции Matrix

0) создать бота в synapse admin
1) pip install synadm выполнить на сервере
2) synadm user login @user:domain.matrix.example - получить секрет (не забыть указать время жизни) или
   curl -X POST "https://domain.matrix.example/_synapse/admin/v1/users/@bot:domain.matrix.example/login" \
   -H "Authorization: Bearer ADMIN_TOKEN" \
   -H "Content-Type: application/json" \
   -d '{
   "valid_until_ms": 1893456000000 // 5 years
   }'
3) Добавить его в чат.
4) Сконфигурировать форму