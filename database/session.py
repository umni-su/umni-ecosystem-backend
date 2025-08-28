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

import time
from contextlib import contextmanager, AbstractContextManager
from sqlmodel import Session
from psycopg2 import OperationalError
from classes.logger.logger import Logger

MAX_RETRIES = 3
RETRY_DELAY = 0.3

# Импортируем engine из engine.py (без циклических зависимостей)
from database.engine import engine


@contextmanager
def write_session(expire_on_commit: bool = True) -> AbstractContextManager[Session]:
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
