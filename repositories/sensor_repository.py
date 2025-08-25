from sqlmodel import select
from starlette.exceptions import HTTPException

from classes.logger import Logger
from classes.storages.device_storage import device_storage
from database.session import write_session
from entities.sensor import Sensor
from models.sensor_model import SensorUpdateModel, SensorModel
from repositories.base_repository import BaseRepository
from starlette.status import HTTP_404_NOT_FOUND


class SensorRepository(BaseRepository):

    @classmethod
    def get_sensor(cls, sensor_id):
        with write_session() as sess:
            try:
                sensor_orm = sess.exec(select(Sensor).where(Sensor.id == sensor_id)).first()
                if sensor_orm is not None:
                    return SensorModel.model_validate(
                        sensor_orm.to_dict()
                    )
                raise HTTPException(
                    status_code=404,
                    detail="Sensor not found"
                )
            except Exception as e:
                Logger.err(str(e))

    @classmethod
    def update_sensor(cls, model: SensorUpdateModel):
        with write_session() as sess:
            try:
                sensor = sess.get(Sensor, model.id)
                if isinstance(sensor, Sensor):
                    sensor.name = model.name

                    if model.cover is not None:
                        photo = device_storage.sensor_cover_upload(
                            sensor=sensor,
                            file=model.cover
                        )
                        sensor.photo = photo

                    sess.add(sensor)
                    sess.commit()
                    sess.refresh(sensor)

                    return SensorModel.model_validate(
                        sensor.to_dict()
                    )
                else:
                    raise HTTPException(
                        status_code=HTTP_404_NOT_FOUND, detail="Sensor not found"
                    )
            except Exception as e:
                Logger.err(str(e))
