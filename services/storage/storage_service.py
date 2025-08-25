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
