from pydantic import BaseModel, ConfigDict


class UserResponseOut(BaseModel):
    id: int
    username: str
    email: str
    firstname: str
    lastname: str


class UserLoginForm(BaseModel):
    username: str
    password: str


class UserResponseIn(UserResponseOut):
    password: str
    password_repeat: str


class UserResponseInDb(UserResponseOut):
    password: str
