from enum import StrEnum
from sqlmodel import Field, SQLModel
from .mixins.created_updated import TimeStampMixin
from entities.mixins.id_column import IdColumnMixin


class ConfigurationKeys(StrEnum):
    APP_INSTALLED = 'app.installed',
    APP_INSTALL_DATE = 'app.install_date',
    APP_LOCALE = 'app.locale',
    APP_UPLOADS_PATH = 'app.uploads_path',
    APP_UPLOADS_MAX_SIZE = 'app.uploads_max_size',
    APP_DEVICE_SYNC_TIMEOUT = 'app.device_sync_timeout',
    APP_KEY = 'app.key',
    MQTT_HOST = 'mqtt.host',
    MQTT_PORT = 'mqtt.port',
    MQTT_USER = 'mqtt.user',
    MQTT_PASSWORD = 'mqtt.password',


class ConfigurationEntityBase:
    key: ConfigurationKeys = Field(index=True)
    value: str | None = Field(index=True, nullable=True)


class ConfigurationEntity(TimeStampMixin, ConfigurationEntityBase, IdColumnMixin, table=True):
    __tablename__ = 'configuration'
