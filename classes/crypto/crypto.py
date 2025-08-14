from cryptography.fernet import Fernet

from classes.logger import logger
from database.database import write_session
from entities.configuration import ConfigurationKeys
import classes.ecosystem as eco


class Crypto:
    key: str | None = None

    def init(self):
        self.load_key()
        logger.info('Init crypto module...')
        return self

    def load_key(self):
        key = eco.ecosystem.config.get_setting(ConfigurationKeys.APP_KEY)
        create: bool = False
        if key is None:
            create = True
        elif key.value is None:
            create = True
        if create:
            with write_session() as session:
                # create key
                f_key = Fernet.generate_key()
                str_key_to_db = f_key.hex()
                key.value = str_key_to_db
                session.add(key)
                session.commit()
                session.refresh(key)
            self.key = key.value
        return bytes.fromhex(key.value)

    def encrypt(self, value: str):
        key: bytes = self.load_key()
        f = Fernet(key)
        encrypt = f.encrypt(str.encode(value))
        return encrypt.decode()

    def decrypt(self, hex: str):
        b = str.encode(hex)
        key: bytes = self.load_key()
        f = Fernet(key)
        decrypt = f.decrypt(b)
        return decrypt.decode()


crypto = Crypto().init()
