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

import typing

from cryptography.fernet import Fernet

from classes.logger import logger
from database.session import write_session
from entities.configuration import ConfigurationKeys

if typing.TYPE_CHECKING:
    from classes.configuration.configuration import EcosystemDatabaseConfiguration


class Crypto:
    key: str | None = None

    def __init__(self, config: "EcosystemDatabaseConfiguration"):
        self.config = config

    def init(self):
        self.load_key()
        logger.info('Init crypto module...')
        return self

    def load_key(self):
        key = self.config.get_setting(ConfigurationKeys.APP_KEY)
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
