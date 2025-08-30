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

from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from sqlmodel import select

from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
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
                        (CameraRecordingEntity.camera_id == camera.id) &
                        (CameraRecordingEntity.end < cutoff_time)
                    )
                ).all()
                return [CameraRecordingModel.model_validate(r.to_dict()) for r in old_recordings]
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)
