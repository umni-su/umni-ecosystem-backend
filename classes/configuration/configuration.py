from sqlmodel import select

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
                print(f'Created {len(created)} items: {",".join(created)}')

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
