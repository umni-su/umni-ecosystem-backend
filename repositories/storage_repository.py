from classes.logger import Logger
from classes.storages.filesystem import Filesystem
from database.session import write_session
from entities.storage import StorageEntity
from models.storage_model import StorageModel, StorageModelBase
from repositories.base_repository import BaseRepository
from sqlmodel import select
from starlette.exceptions import HTTPException

from responses.success import SuccessResponse


class StorageRepository(BaseRepository):

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
        with write_session() as sess:
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
                Logger.err(str(e))

    @classmethod
    def get_storage(cls, storage_id: int):
        with write_session() as sess:
            try:
                storage = sess.get(StorageEntity, storage_id)
                return StorageModel.model_validate(
                    storage.to_dict()
                )
            except Exception as e:
                Logger.err(str(e))

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
                sess.commit()
                sess.refresh(storage)
                return StorageModel.model_validate(
                    storage.to_dict()
                )
            except Exception as e:
                Logger.err(str(e))

    @classmethod
    def update_storage(cls, model: StorageModel):
        with write_session() as sess:
            try:
                cls.path_exists(model.path)
                storage = cls.get_storage(model.id)
                storage.name = model.name
                storage.path = model.path
                storage.active = model.active
                sess.add(storage)
                sess.commit()
                sess.refresh(storage)
                return StorageModel.model_validate(
                    storage.to_dict()
                )
            except Exception as e:
                Logger.err(str(e))

    @classmethod
    def delete_storage(cls, storage_id: int):
        with write_session() as sess:
            try:
                storage = cls.get_storage(storage_id)
                if isinstance(storage, StorageEntity):
                    sess.delete(storage)
                    sess.commit()
                return SuccessResponse(success=True)
            except Exception as e:
                Logger.err(str(e))
