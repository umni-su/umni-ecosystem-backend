from typing import Annotated

import cv2
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from starlette.responses import Response

from classes.auth.auth import Auth
from classes.storages.camera_storage import CameraStorage
from entities.camera import CameraEntity
from models.camera_area_model import CameraAreaBaseModel
from models.camera_model import CameraBaseModel, CameraModelWithRelations
from repositories.area_repository import CameraAreaRepository
from repositories.camera_repository import CameraRepository
from responses.user import UserResponseOut
from services.cameras.cameras_service import CamerasService
from starlette.exceptions import HTTPException

from services.cameras.classes.wheather_detector import WeatherDetector, DayNightDetector

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


@cameras.post('', response_model=CameraModelWithRelations)
def get_cameras(
        model: CameraBaseModel,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        camera: CameraBaseModel = Depends(CameraRepository.add_camera)
):
    return camera


@cameras.put('/{camera_id}', response_model=CameraModelWithRelations)
def get_cameras(
        model: CameraBaseModel,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        camera: CameraBaseModel = Depends(CameraRepository.update_camera)
):
    return camera


@cameras.get('/{camera_id}', response_model=CameraModelWithRelations)
def get_cameras(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        camera: CameraEntity = Depends(CameraRepository.get_camera)
):
    return camera


@cameras.get('/{camera_id}/cover')
def get_camera_cover(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        camera: CameraEntity = Depends(CameraRepository.get_camera)
):
    stream = CamerasService.find_stream_by_camera(camera)
    success, im = cv2.imencode('.jpg', stream.resized)
    print(camera.name, WeatherDetector.detect_weather(stream.resized), DayNightDetector.is_night(stream.resized))
    headers = {'Content-Disposition': f'inline; filename="{camera.id}"'}
    return Response(im.tobytes(), headers=headers, media_type='image/jpeg')


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
    raise HTTPException(
        status_code=422,
        detail='Stream can not be open'
    )


@cameras.post('/{camera_id}/areas')
def save_camera_areas(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        areas: list[CameraAreaBaseModel],
        camera: CameraEntity = Depends(CameraRepository.get_camera),
):
    saved_areas = CameraAreaRepository.save_areas_data(areas, camera)

    return saved_areas
