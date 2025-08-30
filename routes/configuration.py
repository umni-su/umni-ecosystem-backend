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
from fastapi import APIRouter, Depends, HTTPException
from classes.auth.auth import Auth
from classes.l10n.l10n import translator, _
from config.dependencies import get_ecosystem
from models.configuration_model import ConfigurationGroup, ConfigurationModel, ConfigurationModelBase
from repositories.configuration_repository import ConfigurationRepository
from responses.LanguageResponse import LanguageResponse
from responses.user import UserResponseOut

conf = APIRouter(
    prefix='/configuration',
    tags=['configuration']
)


@conf.get('', response_model=list[ConfigurationGroup])
def get_configuration(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    return ConfigurationRepository.get_ecosystem_db_configuration()


@conf.post('', response_model=list[ConfigurationGroup])
def get_configuration(
        config_list: list[ConfigurationModelBase],
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    res = ConfigurationRepository.save_ecosystem_configuration(config_list)
    if res is None:
        raise HTTPException(
            status_code=422,
            detail=_('Failed to save configuration')
        )
    return res


@conf.get('/lang')
def get_lang():
    return translator.get_available_languages()


@conf.put('/lang/{lang}')
def set_set(
        lang: str,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    l = translator.set_language(lang=lang)
    get_ecosystem().config.prepare_groups()

    return LanguageResponse(lang=l)


@conf.get('/lang/{lang}')
def set_set(
        lang: str,
):
    return translator.get_ui_translations_json(lang=lang)


@conf.get('/lang/current', response_model=LanguageResponse)
def get_current_lang():
    return LanguageResponse(
        lang=translator.get_current_language()
    )


@conf.get("/lang/{lang}")
async def get_ui_translations(lang: str):
    """Endpoint для получения UI переводов в JSON"""
    translations = translator.get_ui_translations_json(lang)
    return translations
