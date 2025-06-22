import time
from threading import Thread
import classes.crypto.crypto as crypto

from classes.configuration.configuration import EcosystemDatabaseConfiguration

from classes.logger import logger
from services.service_runner import ServiceRunner


class Ecosystem:
    config: EcosystemDatabaseConfiguration | None
    installed: bool = False
    runner: ServiceRunner | None = None

    def __init__(self):
        Ecosystem.config = EcosystemDatabaseConfiguration()
        Ecosystem.installed = Ecosystem.config.is_installed()
        crypto.Crypto.init()
        thread_init = Thread(
            daemon=True,
            target=self.init_base_config
        )
        thread_init.start()

    def init_base_config(self):
        while not Ecosystem.installed:
            Ecosystem.config.reread()
            Ecosystem.installed = self.config.is_installed()
            logger.warn(f'Ecosystem is not installed. [{time.time()}] Try again after 3 sec...')
            time.sleep(3)
        Ecosystem.installed = True
        logger.info('Ecosystem starting, case installed...')
        self.runner = ServiceRunner()

    @staticmethod
    def is_installed():
        return Ecosystem.installed
