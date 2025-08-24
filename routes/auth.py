from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status, Form, Body

from classes.auth.auth import Auth, Token, ACCESS_TOKEN_EXPIRE_MINUTES
from config.dependencies import get_ecosystem
from entities.user import UserEntity
from responses.auth_check import AuthCheckResponse

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
        user=user.model_dump())


@auth.post("/login", response_model=Token)
def login(
        body: Annotated[UserLoginForm, Depends(), Form()],
        response: Response

):
    user = Auth.authenticate_user(body.username, body.password)
    if not isinstance(user, UserEntity):
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
