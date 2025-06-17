import time
from threading import Thread
import classes.crypto.crypto as crypto

import services.mqtt.mqtt_service as m
from .configuration.configuration import EcosystemDatabaseConfiguration

from classes.storages.device_storage import device_storage
from .logger import logger


class Ecosystem:
    config: EcosystemDatabaseConfiguration | None
    installed: bool = False
    mqtt: m.MqttService | None

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
        self.run_services()

    def run_services(self):
        self.mqtt = m.MqttService()

    @staticmethod
    def is_installed():
        return Ecosystem.installed
