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
from classes.configuration.config_consts import BLANK_PASSWORD
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from config.dependencies import get_ecosystem, get_crypto
from database.session import write_session
from entities.configuration import ConfigurationEntity, ConfigurationKeys
from models.configuration_model import ConfigurationModel, ConfigurationModelBase
from repositories.base_repository import BaseRepository
from sqlmodel import select, col


class ConfigurationRepository(BaseRepository):
    @classmethod
    def get_ecosystem_db_configuration(cls):
        return get_ecosystem().config.groups

    @classmethod
    def save_ecosystem_configuration(cls, config_list: list[ConfigurationModelBase]):
        try:
            with write_session() as session:
                eco = get_ecosystem()
                try:
                    for config in config_list:
                        if config.key not in [
                            ConfigurationKeys.APP_INSTALLED,
                            ConfigurationKeys.APP_INSTALL_DATE
                        ]:
                            config_orm = session.exec(
                                select(ConfigurationEntity).where(col(ConfigurationEntity.key) == config.key)
                            ).first()
                            if isinstance(config_orm, ConfigurationEntity):
                                if config.key == ConfigurationKeys.MQTT_PASSWORD:
                                    if config.value != BLANK_PASSWORD:
                                        config_orm.value = get_crypto().encrypt(config.value)
                                else:
                                    config_orm.value = config.value
                                session.add(config_orm)
                except Exception as e:
                    Logger.err(f'ConfigurationRepository->save_ecosystem_configuration: {str(e)}')
                    return None
            eco.config.reread()
            return eco.config.groups
        except Exception as e:
            Logger.err(f'ConfigurationRepository->save_ecosystem_configuration: {str(e)}')

    @classmethod
    def get_configuration(cls):
        with write_session() as session:
            try:
                excluded_keys = [
                    ConfigurationKeys.APP_INSTALLED,
                    ConfigurationKeys.APP_INSTALL_DATE
                ]
                query = select(ConfigurationEntity)
                query = query.where(
                    col(ConfigurationEntity.key).not_in(excluded_keys)
                )
                _config = session.exec(query).all()
                res: list[ConfigurationModel] = [
                    ConfigurationModel.model_validate(conf.to_dict()) for conf in _config]
                for index, c in enumerate(res):
                    if c.key == ConfigurationKeys.MQTT_PASSWORD and c.value is None:
                        res[index].value = BLANK_PASSWORD

                return res
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)
