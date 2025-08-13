import os
import time
from threading import Thread

from classes.logger import Logger
from classes.websockets.messages.ws_message_storage_size import WebsocketMessageStorageSize
from classes.websockets.websockets import WebSockets
from database.database import write_session
from entities.storage import StorageEntity
from models.storage_model import StorageModelBase
from repositories.storage_repository import StorageRepository
from services.base_service import BaseService


class StorageService(BaseService):

    @staticmethod
    def get_size(start_path='.'):
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(start_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                # skip if it is symbolic link
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
        return total_size

    @classmethod
    def calculate_size(cls, storage_id: int):
        with write_session() as sess:
            storage = sess.get(StorageEntity, storage_id)  # Перезагружаем объект
            while cls.running:
                try:
                    size = StorageService.get_size(storage.path)
                    WebSockets.send_broadcast(
                        WebsocketMessageStorageSize(
                            size=size,
                            storage_id=storage.id
                        )
                    )
                    time.sleep(10)
                except Exception as e:
                    Logger.err(e)

    def run(self):
        storages = StorageRepository.get_storages()
        for storage in storages:
            thread = Thread(
                daemon=True,
                target=self.calculate_size,
                args=[storage.id]
            )
            thread.start()
