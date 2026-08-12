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

from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from classes.storages.filesystem import Filesystem
from database.session import write_session, read_session
from entities.storage import StorageEntity
from models.storage_model import StorageModel, StorageModelBase
from repositories.base_repository import BaseRepository
from sqlmodel import select
from starlette.exceptions import HTTPException

from responses.success import SuccessResponse


class StorageRepository(BaseRepository):
    entity_class = StorageEntity
    model_class = StorageModel

    @classmethod
    def path_exists(cls, path: str):
        if not Filesystem.exists(path):
            raise HTTPException(
                status_code=404,
                detail='Path not found'
            )
        return True

    @classmethod
    def get_storages(cls):
        with read_session() as sess:
            try:
                storages_orm = sess.exec(
                    select(StorageEntity)
                ).all()
                return [
                    StorageModel.model_validate(
                        storage.to_dict()
                    )
                    for storage in storages_orm
                ]
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)

    @classmethod
    def get_storage(cls, storage_id: int):
        with read_session() as sess:
            try:
                storage = sess.get(StorageEntity, storage_id)
                return StorageModel.model_validate(
                    storage.to_dict()
                )
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)

    @classmethod
    def add_storage(cls, model: StorageModelBase):
        with write_session() as sess:
            try:
                cls.path_exists(model.path)
                storage = StorageEntity()
                storage.name = model.name
                storage.path = model.path
                storage.active = model.active
                sess.add(storage)
                ### sess.commit()
                return StorageModel.model_validate(
                    storage.to_dict()
                )
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)

    @classmethod
    def update_storage(cls, model: StorageModel):
        with write_session() as sess:
            try:
                cls.path_exists(model.path)
                storage = sess.get(StorageEntity, model.id)
                if not storage:
                    return None
                storage.name = model.name
                storage.path = model.path
                storage.active = model.active
                sess.add(storage)
                ### sess.commit()
                return StorageModel.model_validate(
                    storage.to_dict()
                )
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)

    @classmethod
    def delete_storage(cls, storage_id: int):
        with write_session() as sess:
            try:
                storage = sess.get(StorageEntity, storage_id)
                if storage is not None:
                    sess.delete(storage)
                return SuccessResponse(success=True)
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)
