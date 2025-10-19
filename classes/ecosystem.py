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

import time
from threading import Thread
from typing import Optional

from classes.configuration.configuration import EcosystemDatabaseConfiguration
from classes.crypto.crypto import Crypto

from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from classes.websockets.events.subscribers import register_non_auto_subscribers as ws_register_non_auto_subscribers
from services.service_runner import ServiceRunner


class Ecosystem:
    config: EcosystemDatabaseConfiguration | None
    installed: bool = False
    service_runner: ServiceRunner | None = None
    _crypto: Crypto | None = None
    _instance: Optional['Ecosystem'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.__initialized = False
        return cls._instance

    def __init__(self):
        if self.__initialized:
            return
        self.__initialized = True
        self.config = EcosystemDatabaseConfiguration()
        self.installed = self.config.is_installed()
        self._crypto = None
        thread_init = Thread(
            daemon=True,
            target=self.init_base_config
        )
        thread_init.start()

    '''
    Register non auto subscribers
    '''

    def register_non_auto_subscribers(self):
        ws_register_non_auto_subscribers()
        Logger.debug('Registered non-auto subscribers for ecosystem', LoggerType.APP)

    @property
    def crypto(self):
        if self._crypto is None:
            self._crypto = Crypto()
        return self._crypto

    def init_base_config(self):
        while not self.installed:
            self.config.reread()
            self.installed = self.config.is_installed()
            Logger.warn(f'Ecosystem is not installed. [{time.time()}] Try again after 3 sec...', LoggerType.APP)
            time.sleep(3)
        self.installed = True
        self.service_runner = ServiceRunner(self.config)

        Logger.info('Ecosystem starting, case installed...', LoggerType.APP)

    def is_installed(self):
        return self.installed
