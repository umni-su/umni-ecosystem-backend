# notifications.py
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
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, status, Depends

from classes.auth.auth import Auth
from classes.l10n.l10n import _
from classes.notifications.notification_service import NotificationService
from models.notification_model import NotificationModel
from models.notification_queue_model import NotificationQueueModel, NotificationQueueBaseModel
from repositories.notification_queue_repository import NotificationQueueRepository
from repositories.notification_repository import NotificationRepository
from responses.user import UserResponseOut

notifications = APIRouter(
    prefix='/notifications',
    tags=['notifications']
)


@notifications.get('')
def get_notifications(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    """Получить все уведомления"""
    return NotificationRepository.get_notifications()


@notifications.get('/{notification_id}')
def get_notification(
        notification_id: int,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)]
):
    """Получить уведомление по ID"""
    notification = NotificationRepository.get_notification(notification_id)
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    return notification


@notifications.get('/{notification_id}/schema')
def get_notification(
        notification_id: int,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)]
):
    """Получить уведомление по ID"""
    notification = NotificationRepository.get_notification(notification_id)
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    return notification.options.get_ui_schema()


@notifications.post('')
def create_notification(
        notification: NotificationModel,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)]
):
    """Создать новое уведомление"""
    # Валидируем конфигурацию
    if not NotificationService.validate_notification_config(
            notification.type,
            notification.options.model_dump() if notification.options else {}
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid notification configuration"
        )

    result = NotificationRepository.create_notification(notification)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create notification"
        )
    return result


@notifications.put('/{notification_id}')
def update_notification(
        notification_id: int,
        notification: NotificationModel,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)]
):
    """Обновить уведомление"""
    # Валидируем конфигурацию
    if not NotificationService.validate_notification_config(
            notification.type,
            notification.options.model_dump() if notification.options else {}
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_("Invalid notification configuration")
        )

    result = NotificationRepository.update_notification(notification_id, notification)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_("Notification not found")
        )
    return result


@notifications.delete('/{notification_id}')
def delete_notification(
        notification_id: int,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)]
):
    """Удалить уведомление"""
    success = NotificationRepository.delete_notification(notification_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    return {"message": "Notification deleted successfully"}


@notifications.post('/test', )
async def test_notification(
        model: NotificationQueueBaseModel,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)]
):
    queue = NotificationQueueModel(
        id=0,
        to=model.to,
        subject=model.subject,
        message=model.message,
        priority=model.priority or 2,
        notification_id=model.notification_id,
        created=datetime.now(),
        updated=datetime.now(),
    )
    success = await NotificationService.send_notification(queue)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_("Failed to send notification")
        )
    return {"message": _("Notification sent successfully")}


@notifications.post('/queue/{queue_id}/send')
async def send_notification(
        queue_id: int,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)]
):
    """Отправить тестовое уведомление"""
    queue = NotificationQueueRepository.get_queue_item(queue_id)
    success = await NotificationService.send_notification(queue)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_("Failed to send notification")
        )
    return {"message": _("Notification sent successfully")}
