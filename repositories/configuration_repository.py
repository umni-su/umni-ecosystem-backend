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

from classes.logger.logger import Logger
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
            try:
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
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)
