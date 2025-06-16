from pydantic import BaseModel


class InitResponse(BaseModel):
    success: bool
