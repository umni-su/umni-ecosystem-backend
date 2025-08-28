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

from sqlmodel import select, col, asc

from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from database.session import write_session
from entities.sensor_entity import SensorEntity
from entities.sensor_history import SensorHistory
from models.sensor_history_model import SearchHistoryModel, SensorHistoryModel
from repositories.base_repository import BaseRepository


class SensorHistoryRepository(BaseRepository):
    @classmethod
    def get_last_record(cls, sensor: SensorEntity) -> None | SensorHistoryModel:
        with write_session() as sess:
            try:
                last = sess.exec(
                    select(SensorHistory)
                    .where(SensorHistory.sensor == sensor)
                    .order_by(
                        col(SensorHistory.created).desc()
                    )
                    .limit(1)
                ).first()
                if isinstance(last, SensorHistory):
                    return SensorHistoryModel.model_validate(last.model_dump())
                return None
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)

    @classmethod
    def get_sensor_history(cls, sensor_id: int, body: SearchHistoryModel):
        with write_session() as sess:
            try:
                start: datetime = body.range[0]
                end: datetime = body.range[1]
                query = select(SensorHistory).where(
                    SensorHistory.sensor_id == sensor_id
                ).where(
                    col(SensorHistory.created).between(
                        start, end
                    )
                ).order_by(
                    asc(SensorHistory.created)
                )
                history: list[SensorHistory] = sess.exec(query).all()
                return [
                    SensorHistoryModel.model_validate(
                        item.to_dict()
                    )
                    for item in history
                ]
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)
