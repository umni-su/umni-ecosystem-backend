from entities.configuration import ConfigurationKeys
from pydantic import BaseModel


class ConfigurationModelBase(BaseModel):
    key: ConfigurationKeys
    value: str | None = None


class ConfigurationModel(ConfigurationModelBase):
    id: int
