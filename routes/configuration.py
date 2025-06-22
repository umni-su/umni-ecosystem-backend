from typing import Annotated

from fastapi import APIRouter, Depends

from classes.auth.auth import Auth
from models.configuration_model import ConfigurationModel
from repositories.configuration_repository import ConfigurationRepository
from responses.user import UserResponseOut

conf = APIRouter(
    prefix='/configuration',
    tags=['configuration']
)


@conf.get('', response_model=list[ConfigurationModel])
def get_configuration(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        config: Annotated[
            list[ConfigurationModel],
            Depends(ConfigurationRepository.get_configuration)
        ]
):
    return config
