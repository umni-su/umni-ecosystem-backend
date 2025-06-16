from pydantic import BaseModel

from responses.user import UserResponseOut


class AuthCheckResponse(BaseModel):
    installed: bool
    authenticated: bool
    user: UserResponseOut | None
