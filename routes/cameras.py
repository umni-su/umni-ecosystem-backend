from typing import Annotated

import cv2
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from starlette.responses import Response

from classes.auth.auth import Auth
from classes.logger import Logger
from models.camera_area_model import CameraAreaBaseModel
from models.camera_event_model import CameraEventModel, CameraEventBaseModel
from models.camera_model import CameraBaseModel, CameraModelWithRelations
from models.pagination_model import PaginatedResponse, EventsPageParams, TimelineParams
from repositories.area_repository import CameraAreaRepository
from repositories.camera_events_repository import CameraEventsRepository
from repositories.camera_repository import CameraRepository
from responses.user import UserResponseOut
from starlette.exceptions import HTTPException

from services.cameras.classes.stream_registry import StreamRegistry
from services.cameras.utils.cameras_helpers import get_no_signal_frame

cameras = APIRouter(
    prefix='/cameras',
    tags=['cameras']
)


@cameras.get('', response_model=list[CameraModelWithRelations])
def get_cameras(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    camera_list = CameraRepository.get_cameras()
    return camera_list


@cameras.post('', response_model=CameraModelWithRelations)
def get_cameras(
        model: CameraBaseModel,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    camera = CameraRepository.add_camera(model)
    return camera


@cameras.put('/{camera_id}', response_model=CameraModelWithRelations)
def get_cameras(
        model: CameraBaseModel,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    camera = CameraRepository.update_camera(model)
    return camera


@cameras.get('/{camera_id}', response_model=CameraModelWithRelations)
def get_cameras(
        camera_id: int,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],

):
    camera = CameraRepository.get_camera(camera_id)
    return camera


@cameras.get('/{camera_id}/cover')
def get_camera_cover(
        camera_id: int,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    camera = CameraRepository.get_camera(camera_id)
    stream = StreamRegistry.find_by_camera(camera)

    if stream is None:
        frame = get_no_signal_frame(width=640)
    else:
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
        camera_id: int,
        user: Annotated[UserResponseOut, Depends(Auth.validate_token)],
):
    camera = CameraRepository.get_camera(camera_id)
    for stream in StreamRegistry.get_all_streams():
        if stream.id == camera.id and stream.opened:
            return StreamingResponse(
                content=stream.generate_frames_async(),
                media_type='multipart/x-mixed-replace; boundary=frame'
            )

    raise HTTPException(
        status_code=422,
        detail='Stream can not be open'
    )


@cameras.post('/{camera_id}/areas', response_model=list[CameraAreaBaseModel])
def save_camera_areas(
        camera_id: int,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        areas: list[CameraAreaBaseModel],
):
    camera = CameraRepository.get_camera(camera_id)
    saved_areas = CameraAreaRepository.save_areas_data(areas, camera)  # TODO fix concurent queries

    return saved_areas


@cameras.delete('/{camera_id}/areas/{area_id}', response_model=list[CameraAreaBaseModel])
def save_camera_areas(
        area_id: int,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    areas = CameraAreaRepository.delete_area(area_id)
    return areas


@cameras.post('/{camera_id}/events', response_model=PaginatedResponse[CameraEventModel])
def save_camera_areas(
        camera_id: int,
        params: EventsPageParams,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    camera = CameraRepository.get_camera(camera_id)
    events = CameraEventsRepository.get_events(params, camera)
    return events


@cameras.post('/{camera_id}/timeline', response_model=list[CameraEventBaseModel])
def get_camera_timeline(
        camera_id: int,
        params: TimelineParams,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    camera = CameraRepository.get_camera(camera_id)
    events = CameraEventsRepository.get_timeline(params, camera)
    return events


@cameras.get('/events/{event_id}/{type}')
def get_camera_area_preview(
        event_id: int,
        type: str,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    try:
        event = CameraEventsRepository.get_event(event_id)
        if type == 'original':
            frame = cv2.imread(event.original, cv2.IMREAD_UNCHANGED)
        else:
            frame = cv2.imread(event.resized, cv2.IMREAD_UNCHANGED)
        success, im = cv2.imencode(ext='.jpg', img=frame)
        if success:
            headers = {'Content-Disposition': f'inline; filename="{event.id}"'}
            return Response(im.tobytes(), headers=headers, media_type='image/jpeg')
        return None
    except Exception as e:
        print(e)
