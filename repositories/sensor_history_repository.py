from datetime import datetime

from sqlmodel import select, col
from entities.sensor import Sensor
from entities.sensor_history import SensorHistory
from models.sensor_history_model import SearchHistoryModel
from repositories.base_repository import BaseRepository


class SensorHistoryRepository(BaseRepository):
    @classmethod
    def get_last_record(cls, sensor: Sensor) -> None | SensorHistory:
        with cls.query() as sess:
            return sess.exec(
                select(SensorHistory)
                .where(SensorHistory.sensor == sensor)
                .order_by(
                    col(SensorHistory.created).desc()
                )
                .limit(1)
            ).first()

    @classmethod
    def get_sensor_history(cls, sensor_id: int, body: SearchHistoryModel):
        with cls.query() as sess:
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
