from datetime import datetime

from sqlmodel import select, col

from database.database import write_session
from entities.sensor import Sensor
from entities.sensor_history import SensorHistory
from models.sensor_history_model import SearchHistoryModel, SensorHistoryModel
from repositories.base_repository import BaseRepository


class SensorHistoryRepository(BaseRepository):
    @classmethod
    def get_last_record(cls, sensor: Sensor) -> None | SensorHistoryModel:
        with write_session() as sess:
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

    @classmethod
    def get_sensor_history(cls, sensor_id: int, body: SearchHistoryModel):
        with write_session() as sess:
            start: datetime = body.range[0]
            end: datetime = body.range[1]
            query = select(SensorHistory).where(
                SensorHistory.sensor_id == sensor_id
            ).where(
                col(SensorHistory.created).between(
                    start, end
                )
            )
            history = sess.exec(query)
            yield history
