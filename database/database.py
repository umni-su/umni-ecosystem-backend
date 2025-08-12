import os.path
import time
from contextlib import contextmanager
from sqlite3 import OperationalError

from sqlmodel import SQLModel, create_engine, Session, text

from classes.logger import Logger
from config.configuration import configuration
from classes.storages.filesystem import Filesystem

# IMPORT MODELS #

import database.entities_imports

MAX_RETRIES = 3  # Максимальное число попыток
RETRY_DELAY = 0.2  # Задержка между попытками (секунды)

fn = os.path.join(configuration.db_dir, configuration.db_source)
filename = f"{fn}"
sqlite_url = f"sqlite:///{filename}"

if not Filesystem.exists(filename):
    Filesystem.mkdir(configuration.db_dir)

connect_args = {
    "check_same_thread": False,
    "timeout": 30
}

engine = create_engine(
    sqlite_url,
    connect_args=connect_args
)

# Включение WAL (однократно при старте приложения)
with Session(engine) as session:
    session.exec(text("PRAGMA journal_mode=WAL;"))
    session.commit()


def create_all():
    SQLModel.metadata.create_all(engine)


# Менеджер сессий с ретраями
@contextmanager
def session_scope(retry_on_locked: bool = True):
    session = None
    for attempt in range(MAX_RETRIES if retry_on_locked else 1):
        try:
            session = Session(engine)
            yield session
            session.commit()
            break
        except OperationalError as e:
            if "database is locked" not in str(e) or not retry_on_locked:
                raise

            Logger.warn(f"Блокировка базы (попытка {attempt + 1}/{MAX_RETRIES})")
            if session:
                session.rollback()
                session.close()

            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            raise
        except Exception:
            if session:
                session.rollback()
            raise
        finally:
            if session and not session.is_active:
                session.close()


def is_database_locked():
    try:
        with Session(engine) as session:
            session.exec(text("SELECT 1;")).first()
        return False
    except OperationalError as e:
        return "database is locked" in str(e)
