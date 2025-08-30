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

from classes.configuration.config_consts import BLANK_PASSWORD
from classes.l10n.l10n import _, translator
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from database.session import write_session
from entities.configuration import ConfigurationEntity, ConfigurationKeys
from models.configuration_model import ConfigurationModel, ConfigurationGroup, ConfigurationModelWithTranslation


class EcosystemDatabaseConfiguration:
    db_config: list[ConfigurationModel] = []
    groups: list[ConfigurationGroup] = []
    language: str = 'ru'

    def __init__(self):
        self.reread()

    def _after_reread(self):
        self.language = self.get_setting(ConfigurationKeys.APP_LOCALE).value or 'en'
        current_language = translator.get_current_language()
        if current_language != self.language:
            translator.set_language(self.language)
            Logger.debug(f'🚩 Set application language to {self.language.upper()}', LoggerType.APP)
        Logger.debug(f'⚙️ Application configuration updated', LoggerType.APP)

    def prepare_groups(self):
        self.groups = []
        app_group = ConfigurationGroup(
            label=_('Base settings'),
            items=[
                ConfigurationModelWithTranslation(
                    key=ConfigurationKeys.APP_LOCALE,
                    translation=_("Application locale"),
                    value=self.get_setting(ConfigurationKeys.APP_LOCALE).value or None
                ),
                ConfigurationModelWithTranslation(
                    key=ConfigurationKeys.APP_UPLOADS_PATH,
                    translation=_("Application uploads path"),
                    value=self.get_setting(ConfigurationKeys.APP_UPLOADS_PATH).value or None
                ),
                ConfigurationModelWithTranslation(
                    key=ConfigurationKeys.APP_UPLOADS_MAX_SIZE,
                    translation=_("Application uploads max size"),
                    value=self.get_setting(ConfigurationKeys.APP_UPLOADS_MAX_SIZE).value or None
                )
            ]
        )

        device_group = ConfigurationGroup(
            label=_('Devices settings'),
            items=[
                ConfigurationModelWithTranslation(
                    key=ConfigurationKeys.APP_DEVICE_SYNC_TIMEOUT,
                    translation=_("Device sync timeout"),
                    value=self.get_setting(ConfigurationKeys.APP_DEVICE_SYNC_TIMEOUT).value or None
                )
            ]
        )

        mqtt_group = ConfigurationGroup(
            label=_('MQTT settings'),
            items=[
                ConfigurationModelWithTranslation(
                    key=ConfigurationKeys.MQTT_HOST,
                    translation=_("MQTT host"),
                    value=self.get_setting(ConfigurationKeys.MQTT_HOST).value or None
                ),
                ConfigurationModelWithTranslation(
                    key=ConfigurationKeys.MQTT_PORT,
                    translation=_("MQTT port"),
                    value=self.get_setting(ConfigurationKeys.MQTT_PORT).value or None
                ),
                ConfigurationModelWithTranslation(
                    key=ConfigurationKeys.MQTT_USER,
                    translation=_("MQTT user"),
                    value=self.get_setting(ConfigurationKeys.MQTT_USER).value or None
                ),
                ConfigurationModelWithTranslation(
                    key=ConfigurationKeys.MQTT_PASSWORD,
                    translation=_("MQTT password"),
                    value=BLANK_PASSWORD if self.get_setting(
                        ConfigurationKeys.MQTT_PASSWORD).value is not None else None
                )
            ]
        )

        self.groups.append(app_group)
        self.groups.append(device_group)
        self.groups.append(mqtt_group)

    def reread(self):
        with write_session() as sess:
            all_config = sess.exec(
                select(ConfigurationEntity)
            ).all()
            self.db_config = [ConfigurationModel.model_validate(conf.to_dict()) for conf in all_config]
            self.check_and_create_configuration_values()
            self.is_installed()
        self._after_reread()
        self.prepare_groups()

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

    def get_setting(self, key: ConfigurationKeys) -> ConfigurationModel | None:
        for conf in self.db_config:
            if conf.key == key:
                return conf
        return None

    def exists(self, key: str):
        for conf in self.db_config:
            if conf.key == key:
                return True
        return False
