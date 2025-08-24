import os.path
from typing import Annotated
from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import FileResponse
from classes.auth.auth import Auth
from classes.logger import Logger
from classes.storages.device_storage import device_storage
from models.device_model import DeviceModelWithRelations, DeviceUpdateModel
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
        Logger.err(e)


@devices.get('/{device_id}', response_model=DeviceModelWithRelations)
def get_device(
        device_id: int,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    try:
        device: DeviceModelWithRelations = DeviceRepository.get_device(device_id)
        return device

    except Exception as e:
        Logger.err(e)


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
        Logger.err(e)


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
        Logger.err(e)


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
        Logger.err(e)
