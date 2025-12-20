# notification_repository.py
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
from datetime import datetime, timedelta

from sqlmodel import delete, col
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from database.session import write_session
from entities.log_entry import LogEntity
from entities.notification import NotificationEntity
from models.log_model import LogModel, LogPageParams
from repositories.base_repository import BaseRepository
from sqlalchemy.sql import or_


class LogRepository(BaseRepository):
    entity_class = LogEntity
    model_class = LogModel

    @classmethod
    def get_logs(cls, params: LogPageParams):
        with write_session() as sess:
            try:
                search_fields = [
                    col(LogEntity.message)
                ]
                if params.term is not None:
                    search_conditions = [field.ilike(f"%{params.term}%") for field in search_fields]
                    where_conditions = [or_(*search_conditions)] if search_conditions else []
                else:
                    where_conditions = []
                if params.level is not None:
                    where_conditions.append(col(LogEntity.level) == params.level)
                if params.logger_type is not None:
                    where_conditions.append(col(LogEntity.logger_type) == params.logger_type)
                if params.code is not None:
                    where_conditions.append(col(LogEntity.code) == params.code.value)
                if params.entity_id is not None:
                    where_conditions.append(col(LogEntity.entity_id) == params.entity_id)
                if params.start is not None and params.end is not None:
                    where_conditions.append(
                        col(LogEntity.timestamp).between(
                            params.start, params.end
                        )
                    )
                elif params.start is not None and params.end is None:
                    where_conditions.append(
                        col(LogEntity.timestamp) >= params.start
                    )
                elif params.end is not None and params.start is None:
                    where_conditions.append(
                        col(LogEntity.timestamp) <= params.end
                    )
                return cls.paginate(
                    session=sess,
                    page_params=params,
                    where_conditions=where_conditions,
                    include_relationships=False,
                    order_by=col(LogEntity.timestamp).desc()
                )
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)
                return False

    @classmethod
    def delete_old_logs(cls, days=90):
        cutoff_time = datetime.now() - timedelta(days=days)
        with write_session() as sess:
            try:
                sess.exec(
                    delete(LogEntity)
                    .where(
                        (col(LogEntity.timestamp) < cutoff_time)
                    )
                )
                Logger.info(f'Clear old logs complete')
            except Exception as e:
                Logger.err(str(e))

    @classmethod
    def delete_log(cls, log_id: int) -> bool:
        with write_session() as sess:
            try:
                log_entity = sess.get(NotificationEntity, log_id)
                if not log_entity:
                    return False

                sess.delete(log_entity)
                sess.commit()
                return True
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)
                return False
