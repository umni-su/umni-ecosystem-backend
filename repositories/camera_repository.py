from entities.camera import CameraEntity
from repositories.base_repository import BaseRepository
from sqlmodel import select


class CameraRepository(BaseRepository):
    @classmethod
    def get_cameras(cls):
        with cls.query() as sess:
            return sess.exec(
                select(CameraEntity)
            ).all()
