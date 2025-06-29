from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from classes.auth.auth import Auth
from classes.storages.camera_storage import CameraStorage
from entities.camera import CameraEntity
from models.camera_model import CameraBaseModel, CameraModelWithRelations
from repositories.camera_repository import CameraRepository
from responses.user import UserResponseOut
from services.cameras.cameras_service import CamerasService

cameras = APIRouter(
    prefix='/cameras',
    tags=['cameras']
)


@cameras.get('')
def get_cameras(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        camera_list: list[CameraBaseModel] = Depends(CameraRepository.get_cameras)
):
    return camera_list


@cameras.post('')
def get_cameras(
        model: CameraBaseModel,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        camera: CameraBaseModel = Depends(CameraRepository.add_camera)
):
    return camera


@cameras.get('/{camera_id}', response_model=CameraModelWithRelations)
def get_cameras(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        camera: CameraEntity = Depends(CameraRepository.get_camera)
):
    return camera


@cameras.get('/{camera_id}/cover/{width}')
def get_cameras(
        width: int,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        camera: CameraEntity = Depends(CameraRepository.get_camera)
):
    return CameraStorage.get_cover(camera, width)


@cameras.get('/{camera_id}/stream')
def get_camera_stream(
        user: Annotated[UserResponseOut, Depends(Auth.validate_token)],
        camera: CameraEntity = Depends(CameraRepository.get_camera)
):
    for stream in CamerasService.streams:
        if stream.id == camera.id:
            return StreamingResponse(
                content=stream.generate_frames(),
                media_type='multipart/x-mixed-replace; boundary=frame'
            )
    return None
