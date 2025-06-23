from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends

from classes.auth.auth import Auth
from models.camera_model import CameraBaseModel
from repositories.camera_repository import CameraRepository
from responses.user import UserResponseOut

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
