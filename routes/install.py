import datetime
from fastapi import APIRouter, HTTPException, Depends, Response, status
from pydantic import BaseModel
from sqlmodel import create_engine
from psycopg2 import OperationalError
from sqlmodel import delete
import classes.ecosystem as eco

from classes.crypto.crypto import crypto
from classes.crypto.hasher import Hasher
from classes.logger import Logger
from config.application_config import base_config
from database.database import write_session
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

router = APIRouter(tags=["setup"])


class DatabaseConfig(BaseModel):
    host: str
    port: int
    name: str
    user: str
    password: str
    admin_user: str = "postgres"
    admin_password: str


@router.post("/api/setup/database/test")
async def test_database_connection(config: DatabaseConfig):
    """Проверка подключения к БД"""
    try:
        # Проверяем подключение с админскими правами
        admin_engine = create_engine(
            f"postgresql+psycopg2://{config.admin_user}:{config.admin_password}@"
            f"{config.host}:{config.port}/postgres",
            connect_args={"connect_timeout": 5}
        )
        with admin_engine.connect() as conn:
            conn.execute("SELECT 1")

        # Проверяем подключение с пользовательскими правами
        user_engine = create_engine(
            f"postgresql+psycopg2://{config.user}:{config.password}@"
            f"{config.host}:{config.port}/{config.name}",
            connect_args={"connect_timeout": 5}
        )
        with user_engine.connect() as conn:
            conn.execute("SELECT 1")

        return {"status": "success", "message": "Connection successful"}
    except OperationalError as e:
        Logger.err(f"Database connection failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/setup/database/save")
async def save_database_config(config: DatabaseConfig):
    """Сохранение конфигурации БД (пароли шифруются)"""
    try:
        # Сохраняем все параметры, пароли в зашифрованном виде
        base_config.update_section('database', {
            'host': config.host,
            'port': str(config.port),
            'name': config.name,
            'user': config.user,
            'password': '',  # Будет заменен на зашифрованный
            'admin_user': config.admin_user,
            'admin_password': ''  # Будет заменен на зашифрованный
        })

        # Шифруем и сохраняем пароли
        base_config.set_encrypted('database', 'password', config.password)
        base_config.set_encrypted('database', 'admin_password', config.admin_password)

        return {"status": "success"}
    except Exception as e:
        Logger.err(f"Failed to save DB config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


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
                        mqtt_password = crypto.encrypt(str(mqtt.password))

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
