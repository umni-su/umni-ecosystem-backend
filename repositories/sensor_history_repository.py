from sqlmodel import select, col

from entities.sensor import Sensor
from entities.sensor_history import SensorHistory
from repositories.base_repository import BaseRepository


class SensorHistoryRepository(BaseRepository):
    @classmethod
    def get_last_record(cls, sensor: Sensor) -> None | SensorHistory:
        with cls.query() as sess:
            return sess.exec(
                select(SensorHistory)
                .where(SensorHistory.sensor == sensor)
                .order_by(
                    col(SensorHistory.created_at).desc()
                )
                .limit(1)
            ).first()
