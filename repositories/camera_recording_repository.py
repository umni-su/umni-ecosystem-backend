from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from sqlmodel import select

from database.database import session_scope
from entities.camera_recording import CameraRecordingEntity
from repositories.base_repository import BaseRepository

if TYPE_CHECKING:
    from entities.camera import CameraEntity


class CameraRecordingRepository(BaseRepository):
    @classmethod
    def get_old_recordings(cls, camera: "CameraEntity") -> list[CameraRecordingEntity]:
        with session_scope() as sess:
            cutoff_time = datetime.now() - timedelta(minutes=camera.delete_after)
            return sess.exec(
                select(CameraRecordingEntity)
                .where(
                    (CameraRecordingEntity.camera == camera) &
                    (CameraRecordingEntity.end < cutoff_time)
                )
            ).all()
