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

from sqlmodel import SQLModel
from database.migrations import MigrationManager
from classes.logger import Logger

# Импортируем engine из отдельного файла
from database.engine import engine

# IMPORT MODELS #
import database.entities_imports


class DatabaseManager:
    def __init__(self):
        self.engine = engine

        if MigrationManager.is_development():
            pass  # Оставляем для возможного создания таблиц

    def _create_tables(self):
        try:
            SQLModel.metadata.create_all(self.engine)
            Logger.info("⏭️ Таблицы созданы (режим разработки)")
        except Exception as e:
            Logger.err(f"⏭️ Ошибка при создании таблиц: {e}")
            raise


db_manager = DatabaseManager()
