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

from contextlib import contextmanager, AbstractContextManager
from sqlmodel import Session

# Импортируем engine из engine.py (без циклических зависимостей)
from database.engine import engine


@contextmanager
def read_session():
    """Сессия только для чтения с отключенным кэшем"""
    session = Session(engine, expire_on_commit=False, autoflush=False)
    try:
        yield session
    finally:
        session.close()


@contextmanager
def write_session(expire_on_commit: bool = True) -> AbstractContextManager[Session]:
    """
    Пишущая сессия: единственная точка фиксации — commit после успешного
    выполнения тела. При исключении — rollback и проброс ошибки наверх.
    """
    session = Session(engine, expire_on_commit=expire_on_commit)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
