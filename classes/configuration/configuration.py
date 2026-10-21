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
        locale = self.get_setting(ConfigurationKeys.APP_LOCALE)
        self.language = locale.value if isinstance(locale, ConfigurationModel) and locale.value is not None else 'ru'
        current_language = translator.get_current_language()
        if current_language != self.language:
            translator.set_language(self.language)
            Logger.debug(f'🚩 Set application language to {self.language.upper()}', LoggerType.APP)
        Logger.debug(f'⚙️ Application configuration updated', LoggerType.APP)

    def prepare_groups(self):
        self.groups = []
        app_group = ConfigurationGroup(
            label=_('Base settings'),
            key='base',
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
            key='devices',
            items=[
                ConfigurationModelWithTranslation(
                    key=ConfigurationKeys.APP_DEVICE_SYNC_TIMEOUT,
                    translation=_("Device sync timeout"),
                    value=self.get_setting(ConfigurationKeys.APP_DEVICE_SYNC_TIMEOUT).value or None
                )
            ]
        )

        self.groups.append(app_group)
        self.groups.append(device_group)

    def reread(self):
        self._refresh_db_config()
        self.check_and_create_configuration_values()
        self._refresh_db_config()  # Обновляем после создания
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
        return conf.value.lower() == 'true' if conf.value is not None else False

    def _refresh_db_config(self):
        with write_session() as sess:
            all_config = sess.exec(
                select(ConfigurationEntity)
            ).all()
            self.db_config = [ConfigurationModel.model_validate(conf.to_dict()) for conf in all_config]

    def check_and_create_configuration_values(self):
        created: [str] = []
        with write_session() as session:
            for _key in ConfigurationKeys:
                # Используем прямой запрос к БД, а не self.exists()
                existing = session.exec(
                    select(ConfigurationEntity).where(ConfigurationEntity.key == _key)
                ).first()
                if not existing:
                    value = None
                    if _key == ConfigurationKeys.APP_DEVICE_SYNC_TIMEOUT:
                        value = str(5)
                    conf: ConfigurationEntity = ConfigurationEntity()
                    conf.key = _key
                    conf.value = value
                    session.add(conf)
                    created.append(_key.value)  # Исправлено: берем значение enum
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
