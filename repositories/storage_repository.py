from classes.storages.filesystem import Filesystem
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
        with cls.query() as sess:
            yield sess.exec(
                select(StorageEntity)
            ).all()

    @classmethod
    def get_storage(cls, storage_id: int):
        with cls.query() as sess:
            return sess.exec(
                select(StorageEntity).where(StorageEntity.id == storage_id)
            ).first()

    @classmethod
    def add_storage(cls, model: StorageModelBase):
        with cls.query() as sess:
            cls.path_exists(model.path)
            storage = StorageEntity()
            storage.name = model.name
            storage.path = model.path
            storage.active = model.active
            sess.add(storage)
            sess.commit()
            sess.refresh(storage)
            return storage

    @classmethod
    def update_storage(cls, model: StorageModel):
        with cls.query() as sess:
            cls.path_exists(model.path)
            storage = cls.get_storage(model.id)
            storage.name = model.name
            storage.path = model.path
            storage.active = model.active
            sess.add(storage)
            sess.commit()
            sess.refresh(storage)
            return storage

    @classmethod
    def delete_storage(cls, storage_id: int):
        with cls.query() as sess:
            storage = cls.get_storage(storage_id)
            if isinstance(storage, StorageEntity):
                sess.delete(storage)
                sess.commit()
            return SuccessResponse(success=True)
