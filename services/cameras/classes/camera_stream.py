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

from datetime import datetime
import os
import random
import threading
import time
from typing import TYPE_CHECKING, Optional, Union

import av
import cv2
import imutils
import numpy as np
from av import VideoFrame
from pydantic import BaseModel

from classes.logger.logger_types import LoggerType
from config.dependencies import get_ecosystem
from classes.logger.logger import Logger
from classes.storages.camera_storage import CameraStorage
from classes.storages.filesystem import Filesystem
from classes.storages.path_map import path_map
from classes.thread.daemon import Daemon

from entities.enums.camera_record_type_enum import CameraRecordTypeEnum
from models.camera_model import CameraModelWithRelations
from models.enums.log_code import LogCode
from models.log_model import LogEntityCode
from repositories.camera_events_repository import CameraEventsRepository
from repositories.camera_repository import CameraRepository
from services.cameras.classes.camera_notifier import CameraNotifier
from services.cameras.classes.stream_registry import StreamRegistry, StreamState
from services.cameras.utils.cameras_helpers import get_no_signal_frame
from services.cameras.webrtc.media_hub import CameraMediaHub, MediaHubRegistry

if TYPE_CHECKING:
    from models.camera_event_model import CameraEventModel
    from services.cameras.classes.roi_tracker import ROIRecordEvent
    from classes.ecosystem import Ecosystem

from services.cameras.classes.roi_tracker import ROIDetectionEvent
from services.cameras.classes.roi_tracker import ROITracker


class ScreenshotResultModel(BaseModel):
    success: bool = False
    directory: str
    filename: str
    ecosystem: "Ecosystem" = None


class CameraStream:
    def __init__(self, camera: CameraModelWithRelations):
        self._stop_requested = False  # Добавляем флаг остановки
        self._stop_event = threading.Event()  # Прерываемый сигнал остановки
        self.ecosystem = get_ecosystem()
        self.id: int = 0
        self.video_pts = 0
        self.audio_pts = 0
        self.tracker: Optional[ROITracker] = None
        self.opened: bool = True
        self.camera: Optional[CameraModelWithRelations] = None
        self.link: Optional[str] = None

        # Timer processing settings
        self.silence_timer: float = 0
        self.silence_pause: float = 1.0

        # Frame processing
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.delay_counter = 0
        self.movement_persistent_counter = 0
        self.first_frame: Optional[np.ndarray] = None
        self.next_frame: Optional[np.ndarray] = None

        # Timing
        self.time_part_start: float = 0
        self.time_prev: float = 0
        self.time_elapsed: float = 0

        # Video frames
        self.original: Optional[Union[np.ndarray | cv2.Mat]] = None
        self.resized: Optional[Union[np.ndarray | cv2.Mat]] = None

        # Threading
        self.daemon: Optional[Daemon] = None

        # Motion detection flags
        self.transient_movement_flag: bool = False
        self.movement_persistent_flag: bool = False
        self.movement_detected: bool = False

        # Storage paths
        self.path: Optional[str] = None
        self.screen_interval: int = 30
        self.screen_timer: float = 0

        # PyAV containers
        self.input_container: Optional[Union[av.container.InputContainer | av.Stream]] = None
        self.output_container: Optional[av.container.OutputContainer] = None
        self.output_stream: Optional[av.Stream] = None
        self.audio_output_stream = None
        self.write: bool = False

        # Error handling
        self.capture_error: Optional[bool] = None
        self.output_file: Optional[str] = None
        self.need_skip: bool = False
        self.need_restart: bool = False

        # Heartbeat
        self.last_frame_time = 0  # Время последнего полученного кадра
        self.heartbeat_timeout = 10  # Максимальное время без кадров (сек)
        self.heartbeat_check_interval = 5  # Интервал проверки (сек)
        self.last_heartbeat_check = 0
        self.restart_delay = 3  # Задержка между попытками перезапуска (сек)
        self.last_restart_time = 0
        self.stop_join_timeout = 6  # Ожидание завершения потока камеры при остановке (сек)
        self.reconnect_initial_delay = 1.0  # Начальная задержка переподключения (сек)
        self.reconnect_max_delay = 30.0  # Максимальная задержка переподключения (сек)

        # For permanent events
        self.permanent_event: Optional["CameraEventModel"] = None

        self._container_lock = threading.RLock()

        # WebRTC: раздача A/V кадров зрителям (создаётся в set_camera)
        self.media_hub: Optional[CameraMediaHub] = None

        # Регистрируем callback для перезапуска
        StreamRegistry.register_restart_callback(self._handle_registry_state_change)
        self._last_registry_state = StreamState.RUNNING

        self.set_camera(camera=camera)
        dmn = 'was_none'

        if isinstance(self.daemon, Daemon):
            if not self.daemon.thread.is_alive():
                self.daemon.thread = None
                self.daemon = None
                dmn = 'was_dead'

        if self.daemon is None:
            self.daemon = Daemon(self.loop_frames)
            Logger.debug(f"👻 [{self.camera.name}] Daemon was created, reason={dmn}", LoggerType.CAMERAS)

    def _handle_registry_state_change(self, new_state: StreamState):
        """Обрабатывает изменения состояния реестра"""
        if self._last_registry_state == new_state:
            return

        self._last_registry_state = new_state

    # Event handlers (unchanged)
    def handle_motion_start(self, event: "ROIDetectionEvent"):
        CameraNotifier.handle_motion_start(event, self)

    def handle_motion_end(self, event: "ROIDetectionEvent"):
        CameraNotifier.handle_motion_end(event, self)

    def handle_recording_start(self, event: "ROIRecordEvent"):
        self.write = True
        CameraNotifier.handle_recording_start(event, self)

    def handle_recording_end(self, event: "ROIRecordEvent"):
        CameraNotifier.handle_recording_end(event, self)

    def prepare_link(self, camera: CameraModelWithRelations, secondary: bool = False):
        userinfo = ''
        if camera.username is not None and camera.password is not None:
            password = self.ecosystem.crypto.decrypt(camera.password)
            userinfo = f'{camera.username}:{password}@'
        stream = camera.primary
        if secondary:
            stream = camera.secondary
        port = 554
        if camera.port is not None:
            port = camera.port
        proto = ''
        if camera.protocol is not None:
            proto = camera.protocol
        return f'{proto.lower()}://{userinfo}{camera.ip}:{port}/{stream}'

    def set_camera(self, camera: CameraModelWithRelations):
        self.need_skip = True
        if self.camera is not None and self.camera.model_dump() != camera.model_dump():
            changed_fields = {
                field: (getattr(self.camera, field), new_value)
                for field, new_value in camera.model_dump().items()
                if hasattr(self.camera, field)
                   and new_value is not None  # Игнорируем None в обновлении
                   and getattr(self.camera, field) != new_value
            }

            if changed_fields and not 'cover' in changed_fields:
                Logger.debug(f"Changes detected in {self.camera.name}: {changed_fields}", LoggerType.CAMERAS)
                if self.camera.active and not camera.active:
                    self.stop()
                else:
                    if not self.opened:
                        self.start()
                    else:
                        self.need_restart = True

        self.camera = camera
        self.id = self.camera.id
        self.link = self.prepare_link(self.camera)
        self.path = os.path.join(path_map.resolve(self.camera.storage.path), str(self.camera.id))

        # WebRTC hub камеры: раздаёт уже декодированные кадры зрителям
        if self.media_hub is None:
            self.media_hub = CameraMediaHub(camera_id=self.id)
            MediaHubRegistry.register(self.media_hub)

        if self.camera.record_mode != camera.record_mode:
            self.destroy_output_container()
            self.time_part_start = 0

        if isinstance(self.tracker, ROITracker):
            self.tracker.update_all_rois(self.camera.areas)

        self.need_skip = False

    def date_filename(self):
        return datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')

    def take_screenshot(self, path: str, prefix: str | None = None, frame: np.ndarray | None = None):
        filename = '.'.join([self.date_filename(), 'jpg'])
        if prefix is not None:
            filename = '.'.join([prefix, filename])

        if not Filesystem.exists(path):
            Filesystem.mkdir(path_or_filename=path, recursive=True)

        full_filename = os.path.join(path, filename)
        _frame = self.original if frame is None else frame
        res = cv2.imwrite(filename=full_filename, img=_frame)

        return ScreenshotResultModel(
            success=res,
            directory=path,
            filename=filename,
        )

    #
    # def get_current_cover(self, w: int) -> str | None:
    #     """Безопасно возвращает текущий кадр"""
    #     return CameraStorage.get_cover(camera=self.camera, width=w)

    def get_current_frame(self) -> np.ndarray:
        """Безопасно возвращает текущий кадр"""
        if self.resized is not None and self.opened:
            return self.resized.copy()  # Делаем копию для потокобезопасности
        return self.get_no_signal_frame()

    def _publish_video_frame(self, frame: av.VideoFrame) -> None:
        """Публикует декодированный видео-кадр WebRTC-зрителям (если они есть)."""
        hub = self.media_hub
        if hub is None or not hub.has_video_subscribers():
            return
        try:
            hub.publish_video(frame)
        except Exception as e:
            Logger.debug(f"[{self.camera.name}] publish_video failed: {e}", LoggerType.CAMERAS)

    def _publish_audio_frame(self, frame: av.AudioFrame) -> None:
        """Публикует декодированный аудио-кадр WebRTC-зрителям (если они есть)."""
        hub = self.media_hub
        if hub is None or not hub.has_audio_subscribers():
            return
        try:
            hub.publish_audio(frame)
        except Exception as e:
            Logger.debug(f"[{self.camera.name}] publish_audio failed: {e}", LoggerType.CAMERAS)

    def _wait_or_stop(self, seconds: float) -> bool:
        """Ждёт указанное время, но просыпается сразу при запросе остановки.

        Возвращает True, если камеру останавливают.
        """
        return self._stop_event.wait(timeout=max(0.0, seconds))

    def _create_input_container(self) -> bool:
        """Открывает входной контейнер с ограниченным экспоненциальным backoff.

        Вместо неограниченной рекурсии выполняет цикл повторов с джиттером,
        который прерывается при остановке камеры.
        Возвращает True при успехе, False если камеру остановили.
        """
        options = {
            'rtsp_transport': 'tcp',
            'timeout': '5000000',  # 5 seconds timeout
            'max_delay': '500000',  # Max packet delay
        }

        delay = self.reconnect_initial_delay
        while not self._stop_requested:
            try:
                self.input_container = av.open(self.link, options=options, timeout=10)
                self.capture_error = False
                if not self.camera.online:
                    CameraRepository.set_online(camera_id=self.camera.id)
                    Logger.info(
                        f"🎉 [{self.camera.name}] Camera online!",
                        LoggerType.CAMERAS,
                        with_db=True,
                        entity_code=LogEntityCode(
                            id=self.camera.id,
                            code=LogCode.CAMERA_ONLINE
                        )
                    )
                Logger.debug(f"🎉 [{self.camera.name}] Start capture on link {self.link}", LoggerType.CAMERAS)
                return True
            except Exception as e:
                self.input_container = None
                self.capture_error = True
                if self.camera.online:
                    CameraRepository.set_online(camera_id=self.camera.id, online=False)
                    Logger.err(
                        f"⚠️ [{self.camera.name}] Camera offline: {e}",
                        LoggerType.CAMERAS,
                        with_db=True,
                        entity_code=LogEntityCode(
                            id=self.camera.id,
                            code=LogCode.CAMERA_OFFLINE
                        )
                    )
                Logger.err(
                    f"⚠️ [{self.camera.name}] Failed to open stream: {e}. Retry in {delay:.1f}s",
                    LoggerType.CAMERAS
                )
                # Экспоненциальный backoff с джиттером, прерываемый остановкой
                jitter = random.uniform(0, delay * 0.3)
                if self._wait_or_stop(delay + jitter):
                    break
                delay = min(delay * 2, self.reconnect_max_delay)

        Logger.debug(f"🛑 [{self.camera.name}] Input container creation stopped", LoggerType.CAMERAS)
        return False

    def create_input_container(self) -> bool:
        if self.input_container is None:
            return self._create_input_container()
        return True

    def stop_input_container(self):
        with self._container_lock:
            if self.input_container is not None:
                self.input_container.close()
                self.input_container = None

    def is_record_permanent(self):
        return self.is_video_mode() or self.is_screenshots_mode()

    def is_screenshots_mode(self):
        return self.camera.record_mode == CameraRecordTypeEnum.SCREENSHOTS

    def is_video_mode(self):
        return self.camera.record_mode == CameraRecordTypeEnum.VIDEO

    def is_video_detection_mode(self):
        return self.camera.record_mode == CameraRecordTypeEnum.DETECTION_VIDEO

    def is_screenshot_detection_mode(self):
        return self.camera.record_mode == CameraRecordTypeEnum.DETECTION_SCREENSHOTS

    def is_detection_mode(self):
        return self.is_screenshot_detection_mode() or self.is_video_detection_mode()

    def stop_write_video(self):
        self.write = False

    def write_frame_safe(self, frame: VideoFrame):
        if self.output_container is None or frame is None:
            return False

        try:
            # Convert numpy array to PyAV frame
            av_frame = frame

            # Ensure the frame has the same format as the stream
            if self.output_stream is not None:
                av_frame = av_frame.reformat(
                    width=self.output_stream.width,
                    height=self.output_stream.height,
                    format=self.output_stream.format
                )

                # Set the PTS (Presentation Time Stamp)
                if not hasattr(self, 'video_pts'):
                    self.video_pts = 0

                # Calculate PTS increment based on time_base and frame rate
                av_frame.pts = self.video_pts
                input_video_stream = self.input_container.streams.video[0]
                fps = input_video_stream.average_rate
                pts_increment = int(self.output_stream.time_base.denominator / fps)
                self.video_pts += pts_increment

                # Encode and write the frame
                for packet in self.output_stream.encode(av_frame):
                    self.output_container.mux(packet)

            return True

        except EOFError as e:
            self.destroy_output_container()
        except Exception as e:
            Logger.err(f"[{self.camera.name}] PyAV Writer Error: {e}", LoggerType.CAMERAS)
            self.destroy_output_container()
            return False

    def is_file_valid(self, filepath: str) -> bool:
        try:
            with av.open(filepath) as container:
                if len(container.streams.video) == 0:
                    return False
                # Проверяем, что можем прочитать первый кадр
                for frame in container.decode(video=0):
                    if frame is not None:
                        return True
                    break
            return False
        except:
            return False

    def destroy_output_container(self):
        with self._container_lock:
            self._destroy_output_container_locked()

    def _destroy_output_container_locked(self):
        if self.output_container is None:
            return

        try:
            # Сначала флашим все данные
            self.flush_output_container()

            # Затем закрываем контейнер
            if self.output_container is not None:
                self.output_container.close()
                Logger.debug(f"🔳️ [{self.camera.name}] Output container stopped: {self.output_file}",
                             LoggerType.CAMERAS)

            # Обработка постоянных событий
            if self.is_record_permanent() and self.permanent_event is not None:
                try:
                    CameraEventsRepository.close_permanent_event(
                        event=self.permanent_event
                    )
                    Logger.debug(f'🎬 [{self.camera.name}] Permanent event end: #ID{self.permanent_event.id}]')
                except Exception as e:
                    Logger.debug(f"[{self.camera.name}] Error closing permanent event: {e}", LoggerType.CAMERAS)

        except Exception as e:
            Logger.debug(f"[{self.camera.name}] Error during container destruction: {e}", LoggerType.CAMERAS)
        finally:
            # Всегда сбрасываем состояние
            self.output_container = None
            self.output_stream = None
            if hasattr(self, 'audio_output_stream'):
                self.audio_output_stream = None
            self.output_file = None
            self.time_part_start = 0
            self.permanent_event = None

    def create_output_container(self, path: str):
        with self._container_lock:
            return self._create_output_container_locked(path)

    def _create_output_container_locked(self, path: str):
        # не стартуем, если поток должен быть закрыт (exit приложения)
        if not self.opened:
            return

        self.video_pts = 0
        self.audio_pts = 0

        if not Filesystem.exists(path):
            Filesystem.mkdir(path, recursive=True)

        filename = f"{self.date_filename()}.mp4"
        full_path = os.path.join(path, filename)

        try:
            # Используем movflags для фрагментированного MP4
            options = {
                'movflags': 'frag_keyframe+empty_moov+default_base_moof',
                # 'fragment_duration': '1000',  # 1 секунда между фрагментами
            }

            # Create output container
            self.output_container = av.open(
                full_path,
                mode='w',
                options=options)

            # Get frame info from input or use defaults
            if self.input_container is not None and len(self.input_container.streams.video) > 0:
                input_video_stream = self.input_container.streams.video[0]
                width = input_video_stream.width
                height = input_video_stream.height
                fps = input_video_stream.average_rate
                codec_name = 'h264'

                # Add video stream to container
                self.output_stream = self.output_container.add_stream(codec_name, rate=fps)
                self.output_stream.width = width
                self.output_stream.height = height
                self.output_stream.pix_fmt = 'yuv420p'
                self.output_stream.time_base = input_video_stream.time_base

                # Add audio stream if exists
                if len(self.input_container.streams.audio) > 0:
                    input_audio_stream = self.input_container.streams.audio[0]
                    in_audio_ctx = input_audio_stream.codec_context
                    self.audio_output_stream = self.output_container.add_stream(
                        'aac',
                        rate=in_audio_ctx.sample_rate,
                        layout=in_audio_ctx.layout.name,
                    )
                    self.audio_output_stream.time_base = input_audio_stream.time_base
            else:
                # Fallback values if no input stream
                width, height = 640, 480
                fps = 25
                codec_name = 'h264'
                self.output_stream = self.output_container.add_stream(codec_name, rate=fps)
                self.output_stream.width = width
                self.output_stream.height = height
                self.output_stream.pix_fmt = 'yuv420p'

            self.output_file = full_path
            Logger.debug(f"[{self.camera.name}] Output container started: {full_path}", LoggerType.CAMERAS)
            return True

        except Exception as e:
            Logger.err(f"[{self.camera.name}] Failed to initialize output container: {e}", LoggerType.CAMERAS)
            self.output_container = None
            self.output_stream = None
            self.audio_output_stream = None
            return False

    def flush_output_container(self):
        if self.output_container is None:
            return

        try:
            # Для видео
            if self.output_stream is not None:
                for packet in self.output_stream.encode(None):  # Flush encoder
                    self.output_container.mux(packet)

            # Для аудио, если есть
            if hasattr(self, 'audio_output_stream') and self.audio_output_stream is not None:
                for packet in self.audio_output_stream.encode(None):
                    self.output_container.mux(packet)

        except Exception as e:
            Logger.err(f"[{self.camera.name}] Error during flush: {e}", LoggerType.CAMERAS)

    def is_stream_alive(self):
        """Проверяет, активен ли поток, включая проверку на зависание"""
        if not self.is_opened():
            return False

        # Проверка на зависание (нет новых кадров)
        current_time = time.time()
        if current_time - self.last_frame_time > self.heartbeat_timeout:
            Logger.warn(f"⚠️ [{self.camera.name}] Stream frozen - no frames for {self.heartbeat_timeout} sec",
                        LoggerType.CAMERAS)
            return False

        try:
            # Быстрая проверка состояния контейнера
            if hasattr(self.input_container, 'is_alive'):
                return self.input_container.is_alive()
            return True
        except (av.error.FFmpegError, EOFError, OSError):
            return False

    def check_heartbeat(self):
        """Периодическая проверка состояния потока"""
        current_time = time.time()
        if current_time - self.last_heartbeat_check > self.heartbeat_check_interval:
            self.last_heartbeat_check = current_time
            if not self.is_stream_alive():
                Logger.warn(f"❤️🩹 [{self.camera.name}] Heartbeat check failed - restarting stream", LoggerType.CAMERAS)
                self.need_restart = True

    def is_opened(self):
        return isinstance(self.input_container, av.container.InputContainer)

    def loop_frames(self):
        first_run: bool = True
        need_create_input = False

        last_flush_time = time.time()
        flush_interval = 30  # Флашим каждые 30 секунд

        if self.input_container is None:
            need_create_input = True

        if need_create_input:
            self.create_input_container()
            Logger.debug(f'[{self.camera.name}] Create input container {self.is_opened()}', LoggerType.CAMERAS)

        if self.tracker is None:
            self.tracker = ROITracker(camera=self.camera)
            self.tracker.set_callbacks(
                motion_start=self.handle_motion_start,
                motion_end=self.handle_motion_end,
                recording_start=self.handle_recording_start,
                recording_end=self.handle_recording_end
            )

        # Initialize PTS counters
        self.video_pts = 0
        self.audio_pts = 0

        while self.camera.active and self.opened and not self._stop_requested:
            try:
                # Проверка heartbeat
                self.check_heartbeat()

                if self._stop_requested:  # Проверка флага остановки
                    break

                if self.need_skip:
                    continue

                # Проверяем, нужно ли перезапустить контейнер
                current_time = time.time()

                # Периодический flush
                if current_time - last_flush_time > flush_interval:
                    with self._container_lock:
                        self.flush_output_container()
                    last_flush_time = current_time

                if self.need_restart:
                    if (current_time - self.last_restart_time) > self.restart_delay:
                        self._perform_restart()
                    else:
                        # Не крутимся в busy-loop до истечения restart_delay
                        self._wait_or_stop(self.restart_delay)
                    continue

                if self.input_container is None:
                    self.create_input_container()
                    continue

                # Читаем пакеты вместо фреймов для лучшей синхронизации
                for packet in self.input_container.demux():
                    self.check_heartbeat()  # Проверка между пакетами

                    # Быстрый выход по запросу остановки или закрытию потока
                    if self._stop_requested or not self.opened:
                        break

                    if self.need_skip or self.need_restart:
                        break

                    # Демультиплексируем пакеты в фреймы
                    for frame in packet.decode():
                        if self._stop_requested or not self.opened:
                            break
                        self.last_frame_time = time.time()  # Обновляем время последнего кадра
                        if isinstance(frame, av.AudioFrame):
                            # WebRTC: раздаём аудио зрителям независимо от записи
                            self._publish_audio_frame(frame)

                            # Обработка аудиофреймов для записи
                            if (hasattr(self, 'audio_output_stream')
                                    and self.audio_output_stream is not None):
                                if self.output_container is not None and self.write:
                                    # Устанавливаем PTS для аудио
                                    if not hasattr(self, 'audio_pts'):
                                        self.audio_pts = 0
                                    frame.pts = self.audio_pts
                                    self.audio_pts += frame.samples

                                    # Кодируем и записываем аудиофрейм
                                    for packet in self.audio_output_stream.encode(frame):
                                        if self.audio_output_stream is not None:
                                            self.output_container.mux(packet)
                                        else:
                                            break
                                else:
                                    self.destroy_output_container()
                            continue

                        if isinstance(frame, av.VideoFrame):
                            # WebRTC: публикуем кадр зрителям до аналитики,
                            # чтобы детекция/запись не «морозили» картинку
                            self._publish_video_frame(frame)

                            now = time.time()
                            pause = now - self.silence_timer
                            elapsed = now - self.screen_timer

                            record_start = self.is_record_permanent() and self.time_part_start == 0
                            cover_due = elapsed > self.screen_interval
                            detection_due = self.is_detection_mode() and (pause > self.silence_pause or first_run is True)

                            # Полный BGR-кадр и 640-ресайз нужны только реальным
                            # потребителям (детекция/обложка/скриншот/событие), а не
                            # каждому кадру при live-просмотре: детекция и так
                            # вызывается не чаще раза в self.silence_pause.
                            if record_start or cover_due or detection_due:
                                self.original = frame.to_ndarray(format='bgr24')
                                self.resized = imutils.resize(self.original, width=640)

                            # Start permanent record or permanent screenshots
                            if record_start:
                                self.time_part_start = now

                                if self.is_screenshots_mode():
                                    res = CameraStorage.take_screenshot(self.camera, self.original)
                                    Logger.debug(
                                        f"[Camera {self.camera.name}] Take screenshot: success={res.success}, fn={res.filename}, dir={res.directory}]",
                                        LoggerType.CAMERAS)
                                elif self.is_video_mode() and (self.output_container is None):
                                    self.create_output_container(CameraStorage.video_path(self.camera))
                                    self.write = True
                                    # Create event
                                    self.permanent_event = CameraEventsRepository.add_permanent_event(
                                        camera=self.camera,
                                        frame=self.original,
                                        record_path=self.output_file
                                    )
                                    Logger.debug(
                                        f'🎬 [{self.camera.name}] Permanent event start: #ID{self.permanent_event.id}]',
                                        LoggerType.CAMERAS)

                                Logger.debug(
                                    f'📽 [{self.camera.name}] with permanent record mode: {self.camera.record_mode}',
                                    LoggerType.CAMERAS)

                            # Take cover
                            if cover_due:
                                CameraStorage.upload_cover(self.camera, self.original)
                                self.screen_timer = now

                            # Write frames to output container if needed
                            with self._container_lock:
                                if self.output_container is not None and self.write:
                                    self.write_frame_safe(frame)
                                else:
                                    self.destroy_output_container()

                            if detection_due:
                                self.tracker.detect_changes(self.resized, self.original)
                                self.silence_timer = now

                            elif self.is_record_permanent():
                                record_part_diff = time.time() - self.time_part_start
                                if record_part_diff > self.camera.record_duration * 60:
                                    self.destroy_output_container()
                                    Logger.debug(f'Camera {self.camera.name} end record video part',
                                                 LoggerType.CAMERAS)

                            first_run = False


            except EOFError as e:
                if not self._stop_requested:  # Проверяем флаг перед обработкой ошибок
                    Logger.warn(f"⚠️ [{self.camera.name}] EOF reached, stream may be disconnected: {e}",
                                LoggerType.CAMERAS)
                    self.need_restart = True
                    self._wait_or_stop(1)
                pass

            except av.error.FFmpegError as e:
                if not self._stop_requested:  # Проверяем флаг перед обработкой ошибок
                    Logger.err(f"⚠️ [{self.camera.name}] FFmpegError: {e}", LoggerType.CAMERAS)
                    self.need_restart = True
                    self.capture_error = True
                    self._wait_or_stop(3)
            except Exception as e:
                if not self._stop_requested:  # Проверяем флаг перед обработкой ошибок
                    Logger.err(f"⚠️ [{self.camera.name}] Unexpected error: {e}", LoggerType.CAMERAS)
                    self.need_restart = True
                    self.capture_error = True
                    self._wait_or_stop(5)
        self.destroy_output_container()
        self.stop_input_container()
        self.output_container = None
        self.input_container = None
        self.opened = False

        if not self._stop_requested:
            Logger.warn(f'⛔️ [{self.camera.name}] stop stream', LoggerType.CAMERAS)

    def _perform_restart(self):
        """Выполняет полный перезапуск потока"""
        Logger.debug(f"🔄 [{self.camera.name}] Performing full restart...", LoggerType.CAMERAS)
        try:
            self.destroy_output_container()
            self.stop_input_container()
            self.create_input_container()
            self.last_frame_time = time.time()  # Сбрасываем таймер кадров
        except Exception as e:
            Logger.err(f"⚠️ [{self.camera.name}] Restart failed: {e}", LoggerType.CAMERAS)
        finally:
            self.need_restart = False
            self.last_restart_time = time.time()

    def get_no_signal_frame(self):
        return get_no_signal_frame(width=640)

    def is_stopped(self):
        return self._stop_requested

    def start(self):
        """Запуск потоков камеры"""
        if self.opened and not self._stop_requested:
            Logger.debug(f"▶️ [{self.camera.name}] Camera stream already running", LoggerType.CAMERAS)
            return

        Logger.debug(f"▶️ [{self.camera.name}] Starting camera stream...", LoggerType.CAMERAS)

        # Сбрасываем флаги
        self._stop_requested = False
        self.opened = True

        # Запускаем демон если он не запущен
        if self.daemon is None or not self.daemon.thread.is_alive():
            self.daemon = Daemon(self.loop_frames)
            Logger.debug(f"👻 [{self.camera.name}] Daemon started", LoggerType.CAMERAS)

        Logger.debug(f"✅ [{self.camera.name}] Camera stream started", LoggerType.CAMERAS)

    def request_stop(self):
        """Быстро выставляет флаги остановки, не дожидаясь завершения потоков.

        Позволяет сначала сигнализировать всем камерам, а затем дождаться их
        завершения параллельно (см. graceful shutdown).
        """
        # Взводим событие до проверки флага: оно прерывает ожидания/backoff
        self._stop_event.set()

        if self._stop_requested:
            return

        Logger.debug(f"🛑 [{self.camera.name}] Stopping camera stream...", LoggerType.CAMERAS)

        self._stop_requested = True
        self.opened = False

    def join_thread(self, timeout: float | None = None) -> bool:
        """Дожидается завершения потока-демона.

        Возвращает True, если поток уже завершился (или его не было).
        """
        daemon_thread = self.daemon.thread if isinstance(self.daemon, Daemon) else None
        if daemon_thread is not None and daemon_thread.is_alive():
            daemon_thread.join(timeout=timeout)
        return not (daemon_thread is not None and daemon_thread.is_alive())

    def finalize_stop(self, daemon_alive: bool):
        """Останавливает трекер и закрывает контейнеры, если поток уже завершился.

        Если поток-демон ещё жив, teardown выполнит сам loop_frames в своём
        finally — закрывать контейнеры извне нельзя (нативный крэш FFmpeg).
        """
        if self.tracker is not None:
            try:
                self.tracker = None
            except Exception as e:
                Logger.debug(f"[{self.camera.name}] Error stopping tracker: {e}", LoggerType.CAMERAS)

        if not daemon_alive:
            self.destroy_output_container()
            self.stop_input_container()

        self.daemon = None

    def stop(self):
        """Корректная остановка всех потоков камеры"""
        if self._stop_requested:
            return

        self.request_stop()

        # Дожидаемся завершения потока-демона, чтобы не закрывать контейнеры,
        # пока он читает/пишет в них (иначе нативный крэш FFmpeg).
        daemon_alive = not self.join_thread(timeout=self.stop_join_timeout)
        if daemon_alive:
            Logger.warn(
                f"⚠️ [{self.camera.name}] Daemon did not stop within {self.stop_join_timeout}s, "
                f"containers will be closed by the stream thread",
                LoggerType.CAMERAS
            )

        self.finalize_stop(daemon_alive)

        Logger.debug(f"✅ [{self.camera.name}] Camera stream stopped completely", LoggerType.CAMERAS)
