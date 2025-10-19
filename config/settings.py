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

from urllib.parse import quote_plus

from pydantic import PostgresDsn
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Настройки БД с дефолтными значениями (для разработки)
    APP_MODE: str = "development"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_SERVER: str = "localhost"
    DB_PORT: int = 5432
    DB_DB: str = "app_db"
    APP_NAME: str = "UMNI Ecosystem"
    API_ROOT: str = "/api"
    LOG_LEVEL: str = 'DEBUG'
    DEBUG_MODE: str = ''
    ENCRYPTION_KEY_FILE: str = '.ecosystem.key'

    # Автоматически создаем DSN строку
    @property
    def database_url(self) -> PostgresDsn:
        encoded_password = quote_plus(self.DB_PASSWORD)
        return PostgresDsn.build(
            scheme="postgresql",
            username=self.DB_USER,
            password=encoded_password,
            host=self.DB_SERVER,
            port=self.DB_PORT,
            path=self.DB_DB,
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Создаем экземпляр настроек
settings = Settings()
