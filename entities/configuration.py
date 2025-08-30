#  Copyright (C) 2025 Mikhail Sazanov
#  #
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#  #
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#  #
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

from enum import StrEnum
from typing import Optional

from sqlmodel import Field

from classes.l10n.l10n import _
from entities.mixins.created_updated import TimeStampMixin
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
    key: Optional[str] = Field(
        unique=True,
        index=True
    )
    value: str | None = Field(
        index=True,
        nullable=True
    )


class ConfigurationEntity(
    TimeStampMixin,
    ConfigurationEntityBase,
    IdColumnMixin,
    table=True
):
    __tablename__ = 'configuration'
