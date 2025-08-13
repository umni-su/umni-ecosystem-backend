import os
import threading
import database.database as db
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from pydantic import BaseModel, field_validator

from classes.logger import Logger
from database.database import write_session
from repositories.camera_events_repository import CameraEventsRepository
from repositories.camera_recording_repository import CameraRecordingRepository
from repositories.camera_repository import CameraRepository


# Pydantic модели
class CleanupReport(BaseModel):
    start_time: datetime
    end_time: Optional[datetime] = None
    processed_cameras: int = 0
    deleted_events: int = 0
    deleted_recordings: int = 0
    deleted_files: int = 0
    execution_time_seconds: Optional[float] = None

    def finalize(self):
        self.end_time = datetime.now()
        if self.start_time and self.end_time:
            self.execution_time_seconds = (self.end_time - self.start_time).total_seconds()


class CleanupConfig(BaseModel):
    cleanup_time: str  # Format "HH:MM"
    min_cleanup_interval_minutes: int = 10
    cleanup_time_tolerance_seconds: int = 30

    @classmethod
    @field_validator('cleanup_time')
    def validate_cleanup_time(cls, value):
        try:
            datetime.strptime(value, "%H:%M")
            return value
        except ValueError:
            raise ValueError("cleanup_time must be in 'HH:MM' format")


class CameraCleanupManager:
    def __init__(self):
        self._active_threads: Dict[int, threading.Thread] = {}
        self._lock = threading.Lock()

    def run_cleanup_for_all_cameras(self):
        """Запускает очистку для всех камер в отдельных потоках"""
        cameras = CameraRepository.get_cameras()

        for camera in cameras:
            if not camera.delete_after:
                continue

            with self._lock:
                # Проверяем, нет ли уже активного потока для этой камеры
                if camera.id in self._active_threads:
                    thread = self._active_threads[camera.id]
                    if thread.is_alive():
                        Logger.debug(f"⚙️ [{camera.name}] Cleanup already running for camera {camera.id}")
                        continue

                # Создаем и запускаем новый поток
                thread = threading.Thread(
                    target=self._clean_camera_data,
                    args=(camera,),
                    daemon=True
                )
                self._active_threads[camera.id] = thread
                thread.start()
                Logger.info(f"⚙️ [{camera.name}] Started cleanup thread for camera {camera.id}")

    def _clean_camera_data(self, camera):
        """Метод для очистки данных конкретной камеры"""
        try:
            Logger.info(f"⚙️ [{camera.name}]Starting cleanup for camera {camera.id}")
            cutoff_time = datetime.now() - timedelta(minutes=camera.delete_after)

            # Очистка событий камеры
            self._clean_camera_events(camera, cutoff_time)

            # Очистка записей камеры
            self._clean_camera_recordings(camera, cutoff_time)

            Logger.info(f"⚙️ [{camera.name}]Cleanup completed for camera {camera.id}")
        except Exception as e:
            Logger.err(f"⚙️ [{camera.name}]Error during cleanup for camera {camera.id}: {str(e)}")
        finally:
            with self._lock:
                self._active_threads.pop(camera.id, None)

    def _clean_camera_events(self, camera, cutoff_time):
        """Очистка событий камеры"""
        with db.write_session() as session:

            events = CameraEventsRepository.get_old_events(camera)

            deleted_count = 0
            for event in events:
                try:
                    # Удаляем связанные файлы
                    for file_path in [event.resized, event.original]:
                        if file_path and os.path.exists(file_path):
                            os.remove(file_path)

                    # Удаляем запись о событии
                    session.delete(event)
                    deleted_count += 1
                except Exception as e:
                    Logger.err(f"🗑️ Error deleting event {event.id}: {str(e)}")

            if deleted_count:
                session.commit()
                Logger.info(f"🗑️ Deleted {deleted_count} events for camera {camera.id}")

    def _clean_camera_recordings(self, camera, cutoff_time):
        """Очистка записей камеры"""
        with write_session() as session:
            recordings = CameraRecordingRepository.get_old_recordings(camera)

            deleted_count = 0
            for recording in recordings:
                try:
                    # Удаляем файл записи
                    if recording.path and os.path.exists(recording.path):
                        os.remove(recording.path)

                    # Удаляем запись о записи
                    session.delete(recording)
                    deleted_count += 1
                except Exception as e:
                    Logger.err(f"🗑️ Error deleting recording {recording.id}: {str(e)}")

            if deleted_count:
                session.commit()
                Logger.info(f"🗑️ Deleted {deleted_count} recordings for camera {camera.id}")

    def get_active_cleanups(self) -> List[int]:
        """Возвращает список ID камер, для которых идет очистка"""
        with self._lock:
            return [cam_id for cam_id, thread in self._active_threads.items() if thread.is_alive()]
