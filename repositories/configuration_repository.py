from database.session import write_session
from entities.configuration import ConfigurationEntity, ConfigurationKeys
from models.configuration_model import ConfigurationModel
from repositories.base_repository import BaseRepository
from sqlmodel import select
from sqlmodel import col


class ConfigurationRepository(BaseRepository):
    @classmethod
    def get_configuration(cls):
        with write_session() as session:
            excluded_keys = [
                ConfigurationKeys.APP_KEY,
                ConfigurationKeys.APP_INSTALLED,
                ConfigurationKeys.APP_INSTALL_DATE
            ]
            query = select(ConfigurationEntity)
            query = query.where(
                col(ConfigurationEntity.key).not_in(excluded_keys)
            )
            _config = session.exec(query).all()
            res: list[ConfigurationModel] = [ConfigurationModel.model_validate(conf.to_dict()) for conf in _config]
            for index, c in enumerate(res):
                if c.key == ConfigurationKeys.MQTT_PASSWORD and c.value is None:
                    res[index].value = '**********'

            return res
