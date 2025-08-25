from classes.logger import Logger
from database.session import write_session
from entities.notification import NotificationEntity
from models.notification_model import NotificationModel
from repositories.base_repository import BaseRepository
from sqlmodel import select
from fastapi import Depends


class NotificationRepository(BaseRepository):
    @classmethod
    def get_notifications(cls):
        with write_session() as sess:
            try:
                notifications_orm = sess.exec(
                    select(NotificationEntity)
                ).all()
                return [
                    NotificationModel.model_validate(
                        n.to_dict()
                    )
                    for n in notifications_orm
                ]
            except Exception as e:
                Logger.err(str(e))

    @classmethod
    def save_notification(cls, model: NotificationModel, target: NotificationEntity):
        with write_session() as sess:
            try:
                # sess.merge(target) вероятно нужно будет
                target.name = model.name
                target.type = model.type
                target.to = model.to
                target.options = model.options

                sess.add(target)
                sess.commit()
                sess.refresh(target)
                return target
            except Exception as e:
                Logger.err(e)

    @classmethod
    def get_notification(cls, notification_id: int):
        with write_session() as sess:
            notification_orm = sess.get(NotificationEntity, notification_id)
            return NotificationModel.model_validate(
                notification_orm.to_dict()
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
