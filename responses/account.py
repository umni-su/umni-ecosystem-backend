from pydantic import BaseModel


class AccountBody(BaseModel):
    email: str
    firstname: str
    lastname: str
    password: str
    passwordConfirm: str
    username: str
