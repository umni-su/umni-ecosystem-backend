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
