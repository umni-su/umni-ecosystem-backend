from typing import Annotated

from fastapi import APIRouter, Depends

from classes.auth.auth import Auth
from responses.user import UserResponseOut
from services.systeminfo.systeminfo_service import SysteminfoService

systeminfo = APIRouter(
    prefix='/systeminfo',
    tags=['systeminfo']
)


@systeminfo.get('')
def get_systeminfo(user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)]):
    return SysteminfoService.info or {}
