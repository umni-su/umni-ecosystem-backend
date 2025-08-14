from threading import Thread

from classes.configuration.configuration import EcosystemDatabaseConfiguration


class BaseService:
    name: str
    thread: Thread | None
    installed: bool = False
    running: bool = True
    config: EcosystemDatabaseConfiguration | None = None

    def __init__(self, config: EcosystemDatabaseConfiguration):
        self.config = config

        self.thread = Thread(
            daemon=True,
            target=self.run_while
        )
        self.thread.start()

    def run_while(self):
        self.run()

    def run(self):
        print('Base')
        return
