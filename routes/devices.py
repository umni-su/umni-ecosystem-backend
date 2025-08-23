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
        device_list: list[DeviceModelWithRelations] = Depends(DeviceRepository.get_devices)
):
    try:
        return device_list

    except Exception as e:
        Logger.err(e)


@devices.get('/{device_id}', response_model=DeviceModelWithRelations)
def get_device(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        device: DeviceModelWithRelations = Depends(DeviceRepository.get_device)
):
    try:
        return device

    except Exception as e:
        Logger.err(e)


'''
Save device
'''


@devices.patch('/{device_id}', response_model=DeviceModelWithRelations)
def update_device(
        model: DeviceUpdateModel,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        device: DeviceModelWithRelations = Depends(DeviceRepository.update_device),
):
    try:
        return device

    except Exception as e:
        Logger.err(e)


@devices.post('/{device_id}/cover', response_model=DeviceModelWithRelations)
def update_device_cover(
        cover: UploadFile,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        device: DeviceModelWithRelations = Depends(DeviceRepository.upload_device_cover),
):
    try:
        return device

    except Exception as e:
        Logger.err(e)


@devices.get('/{device_id}/cover/{width}')
def update_device_cover(
        width: int,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        device: DeviceModelWithRelations = Depends(DeviceRepository.get_device),
):
    try:
        return device_storage.cover_response(device, width)

    except Exception as e:
        Logger.err(e)
