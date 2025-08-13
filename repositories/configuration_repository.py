from database.database import write_session
from entities.configuration import ConfigurationEntity, ConfigurationKeys
from models.configuration_model import ConfigurationModel
from repositories.base_repository import BaseRepository
from sqlmodel import select
from sqlmodel import col


class ConfigurationRepository(BaseRepository):
    @classmethod
    def get_configuration(cls):
        with write_session() as sess:
            config = sess.exec(
                select(ConfigurationEntity).where(
                    col(ConfigurationEntity.key).not_in(
                        [
                            ConfigurationKeys.APP_KEY,
                            ConfigurationKeys.APP_INSTALLED,
                            ConfigurationKeys.APP_INSTALL_DATE
                        ]
                    )
                )
            ).all()
            res: list[ConfigurationModel] = []
            for c in config:
                if c.key == ConfigurationKeys.MQTT_PASSWORD:
                    c.value = '**********'
                res.append(c)

            yield res
