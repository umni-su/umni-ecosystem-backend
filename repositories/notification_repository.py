from classes.logger import Logger
from database.database import session_scope
from entities.notification import NotificationEntity
from models.notification_model import NotificationModel
from repositories.base_repository import BaseRepository
from sqlmodel import select
from fastapi import Depends


class NotificationRepository(BaseRepository):
    @classmethod
    def get_notifications(cls):
        with session_scope() as sess:
            return sess.exec(
                select(NotificationEntity)
            ).all()

    @classmethod
    def save_notification(cls, model: NotificationModel, target: NotificationEntity):
        try:
            target.name = model.name
            target.type = model.type
            target.to = model.to
            target.options = model.options
            with session_scope() as sess:
                sess.add(target)
                sess.commit()
                sess.refresh(target)
                return target
        except Exception as e:
            Logger.err(e)

    @classmethod
    def get_notification(cls, notification_id: int) -> None | NotificationEntity:
        with session_scope() as sess:
            return sess.exec(
                select(NotificationEntity).where(
                    NotificationEntity.id is notification_id
                )
            )

    @classmethod
    def add_notification(cls, model: NotificationModel):
        return cls.save_notification(model, NotificationEntity())

    @classmethod
    def update_notification(cls,
                            model: NotificationModel,
                            notification: Depends(get_notification)
                            ):
        return cls.save_notification(model, notification)
