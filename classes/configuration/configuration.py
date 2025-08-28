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

from sqlmodel import select

from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from database.session import write_session
from entities.configuration import ConfigurationEntity, ConfigurationKeys
from models.configuration_model import ConfigurationModel


class EcosystemDatabaseConfiguration:
    db_config: [ConfigurationModel] = []

    def __init__(self):
        self.reread()

    def reread(self):
        with write_session() as sess:
            all_config = sess.exec(
                select(ConfigurationEntity)
            ).all()
            self.db_config = [ConfigurationModel.model_validate(conf.to_dict()) for conf in all_config]
            self.check_and_create_configuration_values()
            self.is_installed()

    '''
    Check on boot if system is installed
    '''

    def is_installed(self) -> bool:
        if len(self.db_config) == 0:
            return False
        conf = self.get_setting(ConfigurationKeys.APP_INSTALLED)
        if conf is None:
            return False
        return conf.value == 'true'

    def check_and_create_configuration_values(self):
        created: [str] = []
        with write_session() as session:
            for _key in ConfigurationKeys:
                if not self.exists(_key):
                    value = None
                    if _key == ConfigurationKeys.APP_DEVICE_SYNC_TIMEOUT:
                        value = str(5)
                    conf: ConfigurationEntity = ConfigurationEntity()
                    conf.key = _key
                    conf.value = value
                    session.add(conf)
                    created.append(_key)
            if len(created) > 0:
                Logger.debug(f'Created {len(created)} items: {",".join(created)}', LoggerType.APP)

    def get_setting(self, key: str) -> ConfigurationModel | None:
        for conf in self.db_config:
            if conf.key == key:
                return conf
        return None

    def exists(self, key: str):
        for conf in self.db_config:
            if conf.key == key:
                return True
        return False
