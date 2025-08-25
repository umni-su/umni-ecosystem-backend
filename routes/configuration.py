#  Copyright (C) 2025 Mikhail Sazanov
#  #
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#  #
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#  #
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

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
):
    return ConfigurationRepository.get_configuration()
