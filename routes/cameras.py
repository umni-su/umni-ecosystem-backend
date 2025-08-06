from typing import Annotated

import cv2
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from starlette.responses import Response

from classes.auth.auth import Auth
from classes.logger import Logger
from entities.camera import CameraEntity
from models.camera_area_model import CameraAreaBaseModel
from models.camera_event_model import CameraEventModel, CameraEventBase
from models.camera_model import CameraBaseModel, CameraModelWithRelations
from models.pagination_model import PaginatedResponse, EventsPageParams, TimelineParams
from repositories.area_repository import CameraAreaRepository
from repositories.camera_events_repository import CameraEventsRepository
from repositories.camera_repository import CameraRepository
from responses.user import UserResponseOut
from services.cameras.cameras_service import CamerasService
from starlette.exceptions import HTTPException

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
    if stream is None:
        raise HTTPException(status_code=404)

    try:
        if not stream.is_opened() and not stream.resized:
            frame = stream.get_no_signal_frame()
        else:
            frame = stream.resized
    except cv2.error as e:
        frame = stream.get_no_signal_frame()
        Logger.err(f"[{camera.name}] can not get cover with message {e}")

    success, im = cv2.imencode('.jpg', frame)
    headers = {'Content-Disposition': f'inline; filename="{camera.id}"'}
    return Response(im.tobytes(), headers=headers, media_type='image/jpeg')


@cameras.get('/{camera_id}/stream')
def get_camera_stream(
        user: Annotated[UserResponseOut, Depends(Auth.validate_token)],
        camera: CameraEntity = Depends(CameraRepository.get_camera)
):
    for stream in CamerasService.streams:
        if stream.id == camera.id and stream.opened:
            return StreamingResponse(
                content=stream.generate_frames(),
                media_type='multipart/x-mixed-replace; boundary=frame'
            )
    raise HTTPException(
        status_code=422,
        detail='Stream can not be open'
    )


@cameras.post('/{camera_id}/areas', response_model=list[CameraAreaBaseModel])
def save_camera_areas(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        areas: list[CameraAreaBaseModel],
        camera: CameraEntity = Depends(CameraRepository.get_camera),
):
    saved_areas = CameraAreaRepository.save_areas_data(areas, camera)  # TODO fix concurent queries

    return saved_areas


@cameras.delete('/{camera_id}/areas/{area_id}', response_model=list[CameraAreaBaseModel])
def save_camera_areas(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        areas: list[CameraAreaBaseModel] = Depends(CameraAreaRepository.delete_area),
):
    return areas


@cameras.post('/{camera_id}/events', response_model=PaginatedResponse[CameraEventModel])
def save_camera_areas(
        params: EventsPageParams,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        camera: Annotated[CameraEntity, Depends(CameraRepository.get_camera)],

):
    events = CameraEventsRepository.get_events(params, camera)
    return events


@cameras.post('/{camera_id}/timeline', response_model=list[CameraEventBase])
def get_camera_timeline(
        params: TimelineParams,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        camera: Annotated[CameraEntity, Depends(CameraRepository.get_camera)],

):
    events = CameraEventsRepository.get_timeline(params, camera)
    return events


@cameras.get('/events/{event_id}/{type}')
def get_camera_area_preview(
        type: str,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        event: Annotated[CameraEventModel, Depends(CameraEventsRepository.get_event)],

):
    if type == 'original':
        frame = cv2.imread(event.original, cv2.IMREAD_UNCHANGED)
    else:
        frame = cv2.imread(event.resized, cv2.IMREAD_UNCHANGED)
    success, im = cv2.imencode(ext='.jpg', img=frame)
    if success:
        headers = {'Content-Disposition': f'inline; filename="{event.id}"'}
        return Response(im.tobytes(), headers=headers, media_type='image/jpeg')
    return None
