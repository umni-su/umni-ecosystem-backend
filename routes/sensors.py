from typing import Annotated, List

from fastapi import APIRouter, Depends

from classes.auth.auth import Auth
from classes.charts.chart_base import BaseChart
from classes.charts.chart_sensor_history import SensorHistoryChart
from models.sensor_history_model import SensorHistoryModel, SensorHistoryChartModel
from repositories.sensor_history_repository import SensorHistoryRepository
from responses.user import UserResponseOut

sensors = APIRouter(
    prefix='/sensors',
    tags=['sensors']
)


@sensors.get('/{id}')
def get_sensors_history(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    pass


@sensors.post('/{sensor_id}/history')
def get_sensors_history(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        history: Annotated[List[SensorHistoryChartModel], Depends(SensorHistoryRepository.get_sensor_history)]
):
    return SensorHistoryChart(history).series
