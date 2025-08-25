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

from typing import Annotated

from fastapi import APIRouter, Depends, Body, Form, HTTPException

from classes.auth.auth import Auth
from classes.charts.chart_sensor_history import SensorHistoryChart
from classes.logger import Logger
from classes.storages.device_storage import device_storage
from models.sensor_history_model import SearchHistoryModel, SensorHistoryModel
from models.sensor_model import SensorModelWithHistory, SensorUpdateModel, SensorModel
from repositories.sensor_history_repository import SensorHistoryRepository
from repositories.sensor_repository import SensorRepository
from responses.user import UserResponseOut

sensors = APIRouter(
    prefix='/sensors',
    tags=['sensors']
)


@sensors.patch('/{id}')
def get_sensors_history(
        id: int,
        model: Annotated[SensorUpdateModel, Form()],
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    sensor = SensorRepository.update_sensor(model)
    return sensor


@sensors.post('/{sensor_id}/history')
def get_sensors_history(
        sensor_id: int,
        body: Annotated[SearchHistoryModel, Body()],
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    try:
        sensor: SensorModelWithHistory = SensorRepository.get_sensor(sensor_id)
        history: list[SensorHistoryModel] = SensorHistoryRepository.get_sensor_history(
            sensor_id,
            body
        )
        series = SensorHistoryChart(sensor)
        series.set_series(history)
        return series.series
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


@sensors.get('/{sensor_id}/cover/{width}')
def update_device_cover(
        sensor_id: int,
        width: int,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    try:
        sensor: SensorModel = SensorRepository.get_sensor(sensor_id)
        return device_storage.sensor_cover_response(sensor, width)
    except Exception as e:
        Logger.err(e)
