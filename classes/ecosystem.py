import time
from threading import Thread
from typing import Optional

from classes.configuration.configuration import EcosystemDatabaseConfiguration
from classes.crypto.crypto import Crypto

from classes.logger import logger
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

    @property
    def crypto(self):
        if self._crypto is None:
            self._crypto = Crypto(self.config).init()
        return self._crypto

    def init_base_config(self):
        while not self.installed:
            self.config.reread()
            self.installed = self.config.is_installed()
            logger.warn(f'Ecosystem is not installed. [{time.time()}] Try again after 3 sec...')
            time.sleep(3)
        self.installed = True
        self.service_runner = ServiceRunner(self.config)

        logger.info('Ecosystem starting, case installed...')

    def is_installed(self):
        return self.installed
