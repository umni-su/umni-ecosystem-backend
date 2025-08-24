from sqlmodel import create_engine
from config.settings import settings

SQLALCHEMY_ENGINE_OPTIONS = {
    "echo": False,
    "pool_pre_ping": True,
    "pool_recycle": 300,
    "pool_size": 20,
    "max_overflow": 10,
    "connect_args": {
        "connect_timeout": 10,
        "application_name": "umni-backend"
    }
}

# Создаем engine отдельно
engine = create_engine(str(settings.database_url), **SQLALCHEMY_ENGINE_OPTIONS)
