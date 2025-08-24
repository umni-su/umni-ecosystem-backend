import time
from contextlib import contextmanager, AbstractContextManager
from sqlmodel import Session
from psycopg2 import OperationalError
from classes.logger import Logger

MAX_RETRIES = 3
RETRY_DELAY = 0.3

# Импортируем engine из engine.py (без циклических зависимостей)
from database.engine import engine


@contextmanager
def write_session(expire_on_commit: bool = False) -> AbstractContextManager[Session]:
    session = None
    for attempt in range(MAX_RETRIES):
        try:
            session = Session(engine, expire_on_commit=expire_on_commit)
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
