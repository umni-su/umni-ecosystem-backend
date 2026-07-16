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

from datetime import datetime
from fastapi import APIRouter, Response, status
from sqlmodel import delete
from classes.crypto.hasher import Hasher
from classes.logger.logger_types import LoggerType
from config.dependencies import get_ecosystem
from classes.logger.logger import Logger
from database.session import write_session
from entities.configuration import ConfigurationKeys, ConfigurationEntity
from entities.user import UserEntity
from responses.account import AccountBody
from responses.install import InstallBody
from responses.mqtt import MqttBody
from responses.success import SuccessResponse
from cryptography.fernet import InvalidToken

install = APIRouter(
    prefix='/install',
    tags=['install']
)


@install.post('')
def install_ecosystem(body: InstallBody, response: Response):
    try:
        ecosystem = get_ecosystem()
        account: AccountBody = body.account
        mqtt: MqttBody = body.mqtt
        a_password = Hasher.hash(account.password)
        a_password_confirm = account.passwordConfirm
        if len(a_password_confirm) >= 6 \
                and account.password == account.passwordConfirm \
                and len(account.username) >= 3:
            # Delete all users case this is installation

            with write_session() as session:
                statement = delete(UserEntity)
                session.exec(statement)
                # Save user information
                user = UserEntity()
                user.username = account.username
                user.password = a_password
                user.email = account.email
                user.firstname = account.firstname
                user.lastname = account.lastname
                user.is_active = True
                user.is_superuser = True
                session.add(session.merge(user))

                installed = ecosystem.config.get_setting(ConfigurationKeys.APP_INSTALLED)
                installed.value = str(True)
                installed_db = ConfigurationEntity.model_validate(installed)
                session.merge(installed_db)

                install_date = ecosystem.config.get_setting(ConfigurationKeys.APP_INSTALL_DATE)
                install_date.value = str(datetime.now())
                install_date_db = ConfigurationEntity.model_validate(install_date)
                session.merge(install_date_db)
                ecosystem.config.reread()

    except InvalidToken:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        Logger.err('Token error, failed to install Ecosystem', LoggerType.APP)
        return SuccessResponse(success=False)
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        Logger.err(f'Error install {e}', LoggerType.APP)
        return SuccessResponse(success=False)

    response.status_code = 201
    return SuccessResponse(success=True)
