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
