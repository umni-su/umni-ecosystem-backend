import time

from sqlmodel import create_engine, SQLModel, Session, text
from psycopg2 import OperationalError
from contextlib import contextmanager
from config.settings import settings
from classes.logger import Logger

MAX_RETRIES = 3
RETRY_DELAY = 0.3

# IMPORT MODELS #

import database.entities_imports


class DatabaseManager:
    def __init__(self):
        self.engine = create_engine(str(settings.database_url))

        # Создаем таблицы
        SQLModel.metadata.create_all(self.engine)
        Logger.info("Таблицы созданы")

    @contextmanager
    def write_session(self, expire_on_commit: bool = False):
        session = None
        for attempt in range(MAX_RETRIES):
            try:
                session = Session(self.engine, expire_on_commit=expire_on_commit)
                yield session
                session.commit()
                break
            except OperationalError as e:
                Logger.warn(f"Ошибка PostgreSQL (попытка {attempt + 1}/{MAX_RETRIES}): {e}")
                if session:
                    session.rollback()
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
                    continue
                raise
            finally:
                if session:
                    session.close()


db_manager = DatabaseManager()
write_session = db_manager.write_session
