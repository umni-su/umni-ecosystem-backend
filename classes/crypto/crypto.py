from cryptography.fernet import Fernet

from classes.logger import logger
from entities.configuration import ConfigurationKeys
import classes.ecosystem as eco
import database.database as db


class Crypto:
    key: str | None = None

    @staticmethod
    def init():
        Crypto.load_key()
        logger.info('Init crypto module...')

    @staticmethod
    def load_key():
        key = eco.Ecosystem.config.get_setting(ConfigurationKeys.APP_KEY)
        create: bool = False
        if key is None:
            create = True
        elif key.value is None:
            create = True
        if create:
            # create key
            f_key = Fernet.generate_key()
            str_key_to_db = f_key.hex()
            key.value = str_key_to_db
            db.session.add(key)
            db.session.commit()
            db.session.refresh(key)
            Crypto.key = key.value
        return bytes.fromhex(key.value)

    @staticmethod
    def encrypt(value: str):
        key: bytes = Crypto.load_key()
        f = Fernet(key)
        encrypt = f.encrypt(str.encode(value))
        return encrypt.decode()

    @staticmethod
    def decrypt(hex: str):
        b = str.encode(hex)
        key: bytes = Crypto.load_key()
        f = Fernet(key)
        decrypt = f.decrypt(b)
        return decrypt.decode()
