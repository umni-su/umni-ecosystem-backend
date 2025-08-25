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
