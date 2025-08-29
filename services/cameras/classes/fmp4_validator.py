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

import threading
import av
from typing import Optional

from database.session import write_session


class FMP4Validator:
    def __init__(self, engine):
        self.engine = engine
        self.lock = threading.Lock()

    def get_duration_fast(filepath: str) -> float:
        """Получает продолжительность без полного декодирования"""
        try:
            with av.open(filepath) as container:
                if container.duration is None:
                    return 0.0
                return float(container.duration * container.streams.video[0].time_base)
        except:
            return 0.0

    def quick_check(self, filepath: str) -> bool:
        """Быстрая проверка структуры (не блокирующая)"""
        try:
            with open(filepath, 'rb') as f:
                # Проверяем сигнатуры fMP4
                data = f.read(32)
                return (b'ftyp' in data) and (b'moof' in data)
        except:
            return False

    def full_check(self, filepath: str, camera_id: int) -> bool:
        try:
            with av.open(filepath) as container:
                if not container.streams.video:
                    self._update_db(filepath, False, "No video stream")
                    return False

                video_stream = container.streams.video[0]
                time_base = video_stream.time_base  # Получаем из потока

                # Проверка первого кадра
                next(container.decode(video=0))

                # Проверка последнего кадра (если файл не пустой)
                if container.duration is not None:
                    last_pts = int(container.duration * video_stream.time_base) - 1
                    container.seek(last_pts, stream=video_stream)
                    next(container.decode(video=0))

                duration = float(container.duration * time_base) if container.duration else 0.0
                self._update_db(filepath, True, None, duration)
                return True

        except Exception as e:
            self._update_db(filepath, False, str(e))
            return False

    def _update_db(self, filepath: str, is_valid: bool,
                   error: Optional[str], duration: float = 0):
        """Атомарное обновление БД с блокировкой"""
        with self.lock, write_session() as session:
            pass
            # recording = session.exec(
            #     select(CameraRecording)
            #     .where(CameraRecording.file_path == filepath)
            # ).first()
            #
            # if not recording:
            #     recording = CameraRecording(
            #         file_path=filepath,
            #         camera_id=self.camera_id,
            #         is_valid=is_valid,
            #         error_reason=error,
            #         duration=duration
            #     )
            # else:
            #     recording.is_valid = is_valid
            #     recording.error_reason = error
            #     recording.duration = duration
            #     recording.checked_at = datetime.utcnow()

            # session.add(recording)
