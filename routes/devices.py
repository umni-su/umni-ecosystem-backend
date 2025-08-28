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
from fastapi import APIRouter, Depends, UploadFile
from classes.auth.auth import Auth
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from classes.storages.device_storage import device_storage
from models.device_model import DeviceUpdateModel
from models.device_model_relations import DeviceModelWithRelations
from repositories.device_repository import DeviceRepository
from responses.user import UserResponseOut

devices = APIRouter(
    prefix='/devices',
    tags=['devices']
)


@devices.get('', response_model=list[DeviceModelWithRelations])
def get_devices(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    try:
        device_list: list[DeviceModelWithRelations] = DeviceRepository.get_devices()
        return device_list

    except Exception as e:
        Logger.err(str(e), LoggerType.APP)


@devices.get('/{device_id}', response_model=DeviceModelWithRelations)
def get_device(
        device_id: int,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    try:
        device: DeviceModelWithRelations = DeviceRepository.get_device(device_id)
        return device

    except Exception as e:
        Logger.err(str(e), LoggerType.APP)


'''
Save device
'''


@devices.patch('/{device_id}', response_model=DeviceModelWithRelations)
def update_device(
        device_id: int,
        model: DeviceUpdateModel,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    try:
        device: DeviceModelWithRelations = DeviceRepository.update_device(device_id, model)
        return device

    except Exception as e:
        Logger.err(str(e), LoggerType.APP)


@devices.post('/{device_id}/cover', response_model=DeviceModelWithRelations)
def update_device_cover(
        device_id: int,
        cover: UploadFile,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    try:
        device: DeviceModelWithRelations = DeviceRepository.upload_device_cover(device_id, cover)
        return device

    except Exception as e:
        Logger.err(str(e), LoggerType.APP)


@devices.get('/{device_id}/cover/{width}')
def update_device_cover(
        device_id: int,
        width: int,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    try:
        device: DeviceModelWithRelations = DeviceRepository.get_device(device_id)
        return device_storage.cover_response(device, width)

    except Exception as e:
        Logger.err(str(e), LoggerType.APP)
