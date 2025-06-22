from typing import Annotated

from fastapi import APIRouter, Depends

from classes.auth.auth import Auth
from responses.user import UserResponseOut
from services.systeminfo.models.systeminfo_model import SysteminfoModel
from services.systeminfo.systeminfo_service import SysteminfoService

systeminfo = APIRouter(
    prefix='/systeminfo',
    tags=['systeminfo']
)


@systeminfo.get('', response_model=list[SysteminfoModel])
def get_systeminfo(user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)], ):
    return SysteminfoService.history
