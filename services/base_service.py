import time
import classes.ecosystem as eco
from threading import Thread

from classes.logger import Logger


class BaseService:
    name: str
    thread: Thread | None
    installed: bool = False
    running: bool = True

    def __init__(self):
        self.installed = eco.Ecosystem.is_installed()
        self.thread = Thread(
            daemon=True,
            target=self.run_while
        )
        self.thread.start()

    def run_while(self):
        while not self.installed:
            Logger.debug(f'Trying to start service {self.name}')
            self.installed = eco.Ecosystem.is_installed()
            time.sleep(3)
        self.run()

    def run(self):
        print('Base')
        return
