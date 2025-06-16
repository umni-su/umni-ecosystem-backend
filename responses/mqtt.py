from pydantic import BaseModel


class MqttBody(BaseModel):
    host: str
    password: str | int
    port: int = 1883
    user: str
