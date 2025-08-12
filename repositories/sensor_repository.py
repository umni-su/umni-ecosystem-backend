from sqlmodel import select
from starlette.exceptions import HTTPException
from classes.storages.device_storage import device_storage
from database.database import session_scope
from entities.sensor import Sensor
from models.sensor_model import SensorUpdateModel
from repositories.base_repository import BaseRepository
from fastapi import UploadFile
from starlette.status import HTTP_404_NOT_FOUND


class SensorRepository(BaseRepository):

    @classmethod
    def get_sensor(cls, sensor_id):
        with session_scope() as sess:
            yield sess.exec(
                select(Sensor).where(Sensor.id == sensor_id)
            ).first()

    @classmethod
    def update_sensor(cls, model: SensorUpdateModel):

        with session_scope() as sess:
            sensor = sess.exec(
                select(Sensor).where(Sensor.id == model.id)
            ).first()
            if isinstance(sensor, Sensor):
                sensor.name = model.name
                print(isinstance(model.cover, UploadFile))

                if model.cover is not None:
                    photo = device_storage.sensor_cover_upload(
                        sensor=sensor,
                        file=model.cover
                    )
                    sensor.photo = photo

                sess.add(sensor)
                sess.commit()
                sess.refresh(sensor)
                yield sensor
            else:
                raise HTTPException(
                    status_code=HTTP_404_NOT_FOUND, detail="Not found"
                )
