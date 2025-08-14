import time
from threading import Thread

from classes.configuration.configuration import EcosystemDatabaseConfiguration

from classes.logger import logger
from services.service_runner import ServiceRunner


class Ecosystem:
    config: EcosystemDatabaseConfiguration | None
    installed: bool = False
    service_runner: ServiceRunner | None = None

    def __init__(self):
        self.config = EcosystemDatabaseConfiguration()
        self.installed = self.config.is_installed()
        thread_init = Thread(
            daemon=True,
            target=self.init_base_config
        )
        thread_init.start()

    def init_base_config(self):
        self.service_runner = ServiceRunner()
        while not self.installed:
            self.config.reread()
            self.installed = self.config.is_installed()
            logger.warn(f'Ecosystem is not installed. [{time.time()}] Try again after 3 sec...')
            time.sleep(3)
        self.installed = True

        logger.info('Ecosystem starting, case installed...')

    def is_installed(self):
        return self.installed


ecosystem = Ecosystem()
