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

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status, Form, Body

from classes.auth.auth import Auth, Token, ACCESS_TOKEN_EXPIRE_MINUTES
from config.dependencies import get_ecosystem
from entities.user import UserEntity
from responses.auth_check import AuthCheckResponse
from responses.success import SuccessResponse

from responses.user import UserResponseOut, UserLoginForm

auth = APIRouter(
    prefix='/auth',
    tags=['auth']
)


@auth.get('/check', response_model=AuthCheckResponse)
def check_auth(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    ecosystem = get_ecosystem()
    installed = ecosystem.installed
    return AuthCheckResponse(
        installed=installed,
        authenticated=True,
        user=UserResponseOut.model_validate(user.model_dump()))


@auth.post("/login", response_model=Token)
def login(
        body: Annotated[UserLoginForm, Depends(), Form()],
        response: Response

):
    user = Auth.authenticate_user(body.username, body.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = Auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    response.headers["X-Auth-Token"] = access_token
    return Token(
        success=True,
        access_token=access_token,
        token_type="bearer",
        user=UserResponseOut.model_validate(user.model_dump())
    )


@auth.get("/logout", response_model=SuccessResponse)
def logout(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    return SuccessResponse(success=True)
