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