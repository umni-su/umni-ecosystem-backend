from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from sqlmodel import select

from classes.logger import Logger
from database.session import write_session
from entities.camera_recording import CameraRecordingEntity
from models.camera_recording import CameraRecordingModel
from repositories.base_repository import BaseRepository

if TYPE_CHECKING:
    from entities.camera import CameraEntity


class CameraRecordingRepository(BaseRepository):
    @classmethod
    def get_old_recordings(cls, camera: "CameraEntity") -> list[CameraRecordingModel]:
        with write_session() as sess:
            try:
                cutoff_time = datetime.now() - timedelta(minutes=camera.delete_after)
                old_recordings = sess.exec(
                    select(CameraRecordingEntity)
                    .where(
                        (CameraRecordingEntity.camera == camera) &
                        (CameraRecordingEntity.end < cutoff_time)
                    )
                ).all()
                return [CameraRecordingModel.model_validate(r) for r in old_recordings]
            except Exception as e:
                Logger.err(str(e))
