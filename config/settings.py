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
from pathlib import Path
from urllib.parse import quote_plus

from pydantic import PostgresDsn
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Настройки БД с дефолтными значениями (для разработки)
    APP_MODE: str = "development"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "app_db"
    APP_NAME: str = "UMNI Ecosystem"
    API_ROOT: str = "/api"
    LOG_LEVEL: str = 'DEBUG'
    LOG_DIR: str = 'logs'
    LOG_BATCH_SIZE: int = 50
    LOG_FLUSH_INTERVAL: int = 5
    LOG_DB_DELETE_AFTER_DAYS: int = 90
    DEBUG_MODE: str = ''
    ENCRYPTION_KEY: str = ''

    # Корень, куда в контейнере монтируются диски хоста (см. docker-compose.yml).
    # Windows-путь "D:\\folder" резолвится в "<STORAGE_HOST_BASE>/D/folder".
    # На нативной Windows/Linux значение игнорируется, если путь недоступен.
    STORAGE_HOST_BASE: str = '/host'

    # WebRTC (просмотр камер в браузере)
    # STUN-серверы через запятую, напр. "stun:stun.l.google.com:19302".
    # Пусто — только host-кандидаты (локальная сеть).
    WEBRTC_STUN_URLS: str = ''
    # Максимальная ширина видео для WebRTC. 0 — отдавать исходное разрешение.
    WEBRTC_MAX_WIDTH: int = 1920
    # Ширина видео по умолчанию (когда клиент не запросил конкретную).
    # Полный максимум (WEBRTC_MAX_WIDTH) остаётся доступен через set_width.
    WEBRTC_DEFAULT_WIDTH: int = 1280

    # Автоматически создаем DSN строку
    @property
    def database_url(self) -> PostgresDsn:
        encoded_password = quote_plus(self.DB_PASSWORD)
        return PostgresDsn.build(
            # SQLAlchemy 2.1 по умолчанию резолвит "postgresql://" в диалект
            # PGDialect_psycopg (psycopg3), а проект использует psycopg2 —
            # поэтому драйвер указываем явно, иначе падаем с
            # "No module named 'psycopg'".
            scheme="postgresql+psycopg2",
            username=self.DB_USER,
            password=encoded_password,
            host=self.DB_HOST,
            port=self.DB_PORT,
            path=self.DB_NAME,
        )

    class Config:
        # env_file = ".env"
        env_file = "env_config/.env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Создаем экземпляр настроек
settings = Settings()
