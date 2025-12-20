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
from classes.events.event_bus import event_bus
from classes.events.event_types import EventType
from classes.l10n.l10n import _
from database.session import write_session
from entities.log_entry import LogEntity
from models.log_model import LogPageParams
from models.pagination_model import PageParams
from models.sensor_history_model import SearchHistoryModel, SensorHistoryModel
from models.sensor_model import SensorModelWithHistory, SensorUpdateModel
from repositories.log_repository import LogRepository
from repositories.sensor_history_repository import SensorHistoryRepository
from repositories.sensor_repository import SensorRepository
from responses.user import UserResponseOut
from services.mqtt.payload.mqtt_payload_models import MqttSensorPayloadModel

logs = APIRouter(
    prefix='/logs',
    tags=['logs']
)


@logs.post('')
def get_logs(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        params: LogPageParams
):
    return LogRepository.get_logs(params)
