import datetime

from sqlmodel import delete
import database.database as db
import classes.ecosystem as eco
from fastapi import APIRouter, Response, status

from classes.crypto.crypto import Crypto
from classes.crypto.hasher import Hasher
from entities.configuration import ConfigurationKeys
from entities.user import UserEntity
from responses.account import AccountBody
from responses.install import InstallBody
from responses.mqtt import MqttBody
from responses.success import SuccessResponse
from services.mqtt.mqtt_service import MqttService
from cryptography.fernet import InvalidToken

install = APIRouter(
    prefix='/install',
    tags=['install']
)


@install.post('')
def install_ecosystem(body: InstallBody, response: Response):
    try:
        account: AccountBody = body.account
        mqtt: MqttBody = body.mqtt
        a_password = Hasher.hash(account.password)
        a_password_confirm = account.passwordConfirm
        if len(a_password_confirm) >= 6 \
                and account.password == account.passwordConfirm \
                and len(account.username) >= 3:
            # Delete all users case this is installation
            statement = delete(UserEntity)
            session = db.session
            session.execute(statement)
            session.commit()
            # Save user information
            user = UserEntity()
            user.username = account.username
            user.password = a_password
            user.email = account.email
            user.firstname = account.firstname
            user.lastname = account.lastname
            session.add(session.merge(user))

            # Save mqtt info
            if MqttService.check_connection(body.mqtt):

                host = eco.Ecosystem.config.get_setting(ConfigurationKeys.MQTT_HOST)
                host.value = mqtt.host
                session.add(session.merge(host))

                port = eco.Ecosystem.config.get_setting(ConfigurationKeys.MQTT_PORT)
                port.value = mqtt.port
                session.add(session.merge(port))

                if mqtt.password is not None and mqtt.user is not None:
                    mqtt_password = Crypto.encrypt(str(mqtt.password))

                    user = eco.Ecosystem.config.get_setting(ConfigurationKeys.MQTT_USER)
                    user.value = mqtt.user
                    session.add(session.merge(user))

                    pwd = eco.Ecosystem.config.get_setting(ConfigurationKeys.MQTT_PASSWORD)
                    pwd.value = mqtt_password
                    session.add(session.merge(pwd))

            installed = eco.Ecosystem.config.get_setting(ConfigurationKeys.APP_INSTALLED)
            installed.value = True
            session.add(session.merge(installed))

            install_date = eco.Ecosystem.config.get_setting(ConfigurationKeys.APP_INSTALL_DATE)
            install_date.value = datetime.datetime.now()
            session.add(session.merge(install_date))

            session.commit()
            session.refresh(user)
            eco.Ecosystem.config.reread()

    except InvalidToken:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        print('Token error')
        return SuccessResponse(success=False)
    except Exception:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        print('Error install', Exception)
        return SuccessResponse(success=False)

    response.status_code = 201
    return SuccessResponse(success=True)


@install.post('/check/mqtt', response_model=SuccessResponse)
def check_mqtt(mqtt: MqttBody, response: Response):
    connection = MqttService.check_connection(mqtt)
    state = connection.is_connected()
    if state:
        response.status_code = status.HTTP_200_OK
    else:
        response.status_code = status.HTTP_401_UNAUTHORIZED
    connection.disconnect()

    return SuccessResponse(success=state)
