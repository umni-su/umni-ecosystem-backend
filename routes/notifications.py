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
from typing import Annotated

from fastapi import APIRouter, HTTPException, status, Depends

from classes.auth.auth import Auth
from classes.notifications.notification_service import NotificationService
from models.notification_model import NotificationModel
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
            notification.options.dict() if notification.options else {}
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid notification configuration"
        )

    result = NotificationRepository.update_notification(notification_id, notification)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
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


@notifications.post('/{notification_id}/send')
async def send_notification(
        notification_id: int,
        message: str,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)]
):
    """Отправить тестовое уведомление"""
    success = await NotificationService.send_notification(notification_id, message)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send notification"
        )
    return {"message": "Notification sent successfully"}


@notifications.post('/broadcast')
async def broadcast_notification(
        message: str,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)]
):
    """Разослать сообщение всем активным уведомлениям"""
    results = await NotificationService.broadcast_message(message)
    success_count = sum(results)
    return {
        "message": f"Notification sent to {success_count} of {len(results)} recipients",
        "results": results
    }
