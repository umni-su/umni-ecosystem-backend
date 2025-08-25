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

from datetime import timezone, datetime, timedelta
from typing import Annotated
import jwt
from fastapi import (
    HTTPException, Depends, Cookie, Query,
    Response, WebSocket, WebSocketException,
    status
)
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from pydantic import BaseModel
from sqlmodel import select

from classes.crypto.hasher import Hasher
from config.dependencies import get_ecosystem
from classes.logger import Logger
from database.session import write_session
from entities.configuration import ConfigurationKeys
from entities.user import UserEntity

from responses.unauthenticated_response import UnauthenticatedResponse
from responses.user import UserResponseOut, UserResponseInDb

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class Auth:
    # to get a string like this run:
    # openssl rand -hex 32

    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

    @staticmethod
    def get_ecosystem():
        return get_ecosystem()

    @staticmethod
    def verify_password(plain_password, hashed_password):
        return Hasher.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password):
        return Hasher.hash(password)

    @staticmethod
    def get_user(username: str) -> UserResponseInDb:
        with write_session() as session:
            user = session.exec(
                select(UserEntity).where(UserEntity.username == username)
            ).first()
            if not user:
                raise HTTPException(detail="User not found", status_code=404)
            return UserResponseInDb.model_validate(user.model_dump())

    @staticmethod
    def authenticate_user(username: str, password: str):
        user = Auth.get_user(username)
        if not user:
            return None
        if not Auth.verify_password(password, user.password):
            return None
        return user

    @staticmethod
    def create_access_token(
            data: dict,
            expires_delta: timedelta | None = None
    ):
        ecosystem = Auth.get_ecosystem()
        key = ecosystem.config.get_setting(ConfigurationKeys.APP_KEY).value
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, key, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], response: Response):
        ecosystem = Auth.get_ecosystem()
        key = ecosystem.config.get_setting(ConfigurationKeys.APP_KEY).value
        installed = ecosystem.is_installed()

        install_exception = HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Ecosystem is not installed",
            headers={"WWW-Authenticate": "Bearer"},
        )

        if not installed:
            raise install_exception
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=UnauthenticatedResponse(
                authenticated=False,
                message="Could not validate credentials"
            ).model_dump(),
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, key, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
            token_data = TokenData(username=username)
        except InvalidTokenError:
            raise credentials_exception
        user = Auth.get_user(username=token_data.username)
        if user is None:
            raise credentials_exception
        exp: int = payload.get("exp")
        expires = datetime.fromtimestamp(exp)
        diff = expires - datetime.now()
        remains_min = diff.seconds / 60
        if remains_min <= ACCESS_TOKEN_EXPIRE_MINUTES / 5:
            Logger.debug(f"Refresh token for user {username}")
            access_token = Auth.create_access_token(
                data={"sub": user.username},
                expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            )
            response.headers["X-Refresh-Token"] = access_token

        return user

    @staticmethod
    def get_current_active_user(
            current_user: Annotated[UserResponseOut, Depends(get_current_user)]
    ):
        # if current_user.disabled:
        #     raise HTTPException(status_code=400, detail="Inactive user")
        return current_user

    @staticmethod
    def validate_token(
            token: Annotated[str | None, Query()] = None
    ):
        auth_exception: HTTPException = HTTPException(
            status_code=403,
            detail='You are not authorize'
        )
        try:
            ecosystem = Auth.get_ecosystem()
            key = ecosystem.config.get_setting(ConfigurationKeys.APP_KEY).value
            payload = jwt.decode(token, key, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise auth_exception
            token_data = TokenData(username=username)
        except InvalidTokenError:
            raise auth_exception
        user = Auth.get_user(username=token_data.username)
        if user is None:
            raise auth_exception
        return user

    @staticmethod
    async def validate_ws_token(
            websocket: WebSocket,
            session: Annotated[str | None, Cookie()] = None,
            token: Annotated[str | None, Query()] = None,
    ):
        if session is None and token is None:
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
        try:
            ecosystem = Auth.get_ecosystem()
            key = ecosystem.config.get_setting(ConfigurationKeys.APP_KEY).value
            payload = jwt.decode(token, key, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise WebSocketException(
                    code=status.WS_1008_POLICY_VIOLATION
                )
            token_data = TokenData(username=username)
        except InvalidTokenError:
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION
            )
        user = Auth.get_user(username=token_data.username)
        if user is None:
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION
            )
        return user


class Token(BaseModel):
    success: bool
    access_token: str
    token_type: str
    user: None | UserResponseOut = None


class TokenData(BaseModel):
    username: str | None = None
