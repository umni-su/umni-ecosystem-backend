from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuration(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')
    app_name: str = "UMNI Ecosystem"
    api_root: str = "/api"
    db_dir: str = "database/source/"
    db_source: str = "database.db"


configuration = Configuration()
