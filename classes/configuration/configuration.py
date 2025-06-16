from typing import Sequence

from sqlmodel import Session, select

from entities.configuration import ConfigurationEntity, ConfigurationKeys
from database.database import session


class EcosystemDatabaseConfiguration:
    session: Session
    db_config: [ConfigurationEntity] = []

    def __init__(self):
        self.reread()

    def reread(self):
        self.session = session
        self.db_config = self.session.exec(
            select(ConfigurationEntity)
        ).all()
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
        return conf.value == '1'

    def check_and_create_configuration_values(self):
        created: [str] = []
        for _key in ConfigurationKeys:
            if not self.exists(_key):
                value = None
                if _key == ConfigurationKeys.APP_DEVICE_SYNC_TIMEOUT:
                    value = str(5)
                conf: ConfigurationEntity = ConfigurationEntity()
                conf.key = _key
                conf.value = value
                self.session.add(conf)
                self.session.commit()
                created.append(_key)
        if len(created) > 0:
            print(f'Created {len(created)} items: {",".join(created)}')

    def get_setting(self, key: str) -> ConfigurationEntity | None:
        for conf in self.db_config:
            if conf.key == key:
                return conf
        return None

    def exists(self, key: str):
        for conf in self.db_config:
            if conf.key == key:
                return True
        return False
