import os
import time
from threading import Thread
from pydantic import BaseModel
from classes.logger import Logger
from classes.websockets.messages.ws_message_storage_size import WebsocketMessageStorageSize
from classes.websockets.websockets import WebSockets
from database.session import write_session
from entities.storage import StorageEntity
from repositories.storage_repository import StorageRepository
from services.base_service import BaseService


class StorageTask(BaseModel):
    storage_id: int
    thread: Thread | None = None

    class Config:
        arbitrary_types_allowed = True


class StorageService(BaseService):
    name = 'storage'
    tasks: list[StorageTask] = []

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
            try:
                WebSockets.send_broadcast(
                    WebsocketMessageStorageSize(
                        storage_id=storage.id,
                        storage_path=storage.path
                    )
                )
            except Exception as e:
                Logger.err(e)

    def run(self):
        while self.running:
            storages = StorageRepository.get_storages()
            for storage in storages:
                thread = Thread(
                    daemon=False,
                    target=self.calculate_size,
                    args=[storage.id]
                )
                thread.start()
                thread.join(timeout=5)
            time.sleep(10)
