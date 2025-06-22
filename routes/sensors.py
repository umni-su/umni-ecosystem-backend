from typing import Annotated

from fastapi import APIRouter, Depends, Body, Form, UploadFile

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
        model: Annotated[SensorUpdateModel, Form()],
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        sensor: Annotated[SensorModelWithHistory, Depends(SensorRepository.update_sensor)]
):
    return sensor


@sensors.post('/{sensor_id}/history')
def get_sensors_history(
        body: Annotated[SearchHistoryModel, Body()],
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        sensor: Annotated[SensorModelWithHistory, Depends(SensorRepository.get_sensor)],
        history: Annotated[list[SensorHistoryModel], Depends(SensorHistoryRepository.get_sensor_history)]
):
    series = SensorHistoryChart(sensor)
    series.set_series(history)
    return series.series


@sensors.get('/{sensor_id}/cover/{width}')
def update_device_cover(
        width: int,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        sensor: SensorModel = Depends(SensorRepository.get_sensor),
):
    try:
        return device_storage.sensor_cover_response(sensor, width)

    except Exception as e:
        Logger.err(e)
