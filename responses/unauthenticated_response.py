from pydantic import BaseModel


class UnauthenticatedResponse(BaseModel):
    message: str
    authenticated: bool
