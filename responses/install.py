from pydantic import BaseModel

from responses.account import AccountBody
from responses.mqtt import MqttBody


class InstallBody(BaseModel):
    account: AccountBody
    mqtt: MqttBody
