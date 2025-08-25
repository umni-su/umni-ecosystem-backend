import datetime
import os
import threading
import time
from typing import TYPE_CHECKING, Optional, Union

import av
import cv2
import imutils
import numpy as np
from av import VideoFrame
from pydantic import BaseModel

from config.dependencies import get_ecosystem
from classes.logger import Logger
from classes.storages.camera_storage import CameraStorage
from classes.storages.filesystem import Filesystem
from classes.thread.Daemon import Daemon

from entities.enums.camera_record_type_enum import CameraRecordTypeEnum
from models.camera_model import CameraModelWithRelations
from repositories.camera_events_repository import CameraEventsRepository
from services.cameras.classes.camera_notifier import CameraNotifier

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
        self.ecosystem = get_ecosystem()
        self.id: int = 0
        self.video_pts = 0
        self.audio_pts = 0
        self.tracker: Optional[ROITracker] = None
        self.opened: bool = True
        self.camera: Optional[CameraModelWithRelations] = None
        self.link: Optional[str] = None

        # Video processing settings
        self.frames_skip: int = 20
        self.detection_size: int = 5000
        self.detection_persistent: int = 100
        self.silence_timer: float = 0
        self.silence_pause: int = 10

        # Frame processing
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.delay_counter = 0
        self.movement_persistent_counter = 0
        self.first_frame: Optional[np.ndarray] = None
        self.next_frame: Optional[np.ndarray] = None
        self.fps: int = 10

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

        # For permanent events
        self.permanent_event: Optional["CameraEventModel"] = None

        self._container_lock = threading.Lock()

        self.set_camera(camera=camera)
        dmn = 'was_none'

        if isinstance(self.daemon, Daemon):
            if not self.daemon.thread.is_alive():
                self.daemon.thread = None
                self.daemon = None
                dmn = 'was_dead'

        if self.daemon is None:
            self.daemon = Daemon(self.loop_frames)
            Logger.debug(f"👻 [{self.camera.name}] Daemon was created, reason={dmn}")

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

            if changed_fields:
                print(f"Changes detected in {self.camera.name}: {changed_fields}")
                self.need_restart = True
                time.sleep(2)
                Logger.warn(f'{self.camera.name} was changed! Changes: {changed_fields}')
                self.need_restart = True

        self.camera = camera
        self.id = self.camera.id
        self.link = self.prepare_link(self.camera)
        self.path = os.path.join(self.camera.storage.path, str(self.camera.id))

        if self.camera.record_mode != camera.record_mode:
            self.destroy_output_container()
            self.time_part_start = 0

        if isinstance(self.tracker, ROITracker):
            self.tracker.update_all_rois(self.camera.areas)

        self.need_skip = False

    def date_filename(self):
        return datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')

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

    def _create_input_container(self):
        options = {
            'rtsp_transport': 'tcp',
            'stimeout': '5000000',  # 5 seconds timeout
            'max_delay': '500000',  # Max packet delay
        }

        try:
            self.input_container = av.open(self.link, options=options, timeout=10)
            self.capture_error = False
            Logger.debug(f"🎉 [{self.camera.name}] Start capture on link {self.link}")
        except Exception as e:
            self.capture_error = True
            Logger.debug(f"⚠️ [{self.camera.name}] Failed to open stream: {e}")
            time.sleep(3)
            self._create_input_container()

    def create_input_container(self):
        if self.input_container is None:
            self._create_input_container()

    def stop_input_container(self):
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
            Logger.err(f"[{self.camera.name}] PyAV Writer Error: {e}")
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
        if self.output_container is None:
            return

        try:
            # Сначала флашим все данные
            self.flush_output_container()

            # Затем закрываем контейнер
            if self.output_container is not None:
                self.output_container.close()
                Logger.debug(f"🔳️ [{self.camera.name}] Output container stopped: {self.output_file}")

            # Обработка постоянных событий
            if self.is_record_permanent() and self.permanent_event is not None:
                try:
                    CameraEventsRepository.close_permanent_event(
                        event=self.permanent_event
                    )
                    Logger.debug(f'🎬 [{self.camera.name}] Permanent event end: #ID{self.permanent_event.id}]')
                except Exception as e:
                    Logger.debug(f"[{self.camera.name}] Error closing permanent event: {e}")

        except Exception as e:
            Logger.debug(f"[{self.camera.name}] Error during container destruction: {e}")
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
                'fragment_duration': '1000',  # 1 секунда между фрагментами
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
            Logger.debug(f"[{self.camera.name}] Output container started: {full_path}")
            return True

        except Exception as e:
            Logger.err(f"[{self.camera.name}] Failed to initialize output container: {e}")
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
            Logger.err(f"[{self.camera.name}] Error during flush: {e}")

    def is_stream_alive(self):
        """Проверяет, активен ли поток, включая проверку на зависание"""
        if not self.is_opened():
            return False

        # Проверка на зависание (нет новых кадров)
        current_time = time.time()
        if current_time - self.last_frame_time > self.heartbeat_timeout:
            Logger.warn(f"⚠️ [{self.camera.name}] Stream frozen - no frames for {self.heartbeat_timeout} sec")
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
                Logger.warn(f"❤️🩹 [{self.camera.name}] Heartbeat check failed - restarting stream")
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
            Logger.debug(f'[{self.camera.name}] Create input container {self.is_opened()}')

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

        while self.camera.active or self.opened:
            try:
                # Проверка heartbeat
                self.check_heartbeat()

                if self.need_skip:
                    continue

                # Проверяем, нужно ли перезапустить контейнер
                current_time = time.time()

                # Периодический flush
                if current_time - last_flush_time > flush_interval:
                    with self._container_lock:
                        self.flush_output_container()
                    last_flush_time = current_time

                if self.need_restart and (current_time - self.last_restart_time) > self.restart_delay:
                    self._perform_restart()
                    continue

                if self.input_container is None:
                    self.create_input_container()
                    continue

                # Читаем пакеты вместо фреймов для лучшей синхронизации
                for packet in self.input_container.demux():
                    self.check_heartbeat()  # Проверка между пакетами
                    if not self.camera.active and not self.opened:
                        break

                    if not self.camera.active and not self.opened:
                        break

                    if self.need_skip or self.need_restart:
                        break

                    # Демультиплексируем пакеты в фреймы
                    for frame in packet.decode():
                        self.last_frame_time = time.time()  # Обновляем время последнего кадра
                        if isinstance(frame, av.AudioFrame) and hasattr(self,
                                                                        'audio_output_stream') and self.audio_output_stream is not None:
                            # Обработка аудиофреймов
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
                            # Обработка видеофреймов
                            self.original = frame.to_ndarray(format='bgr24')
                            self.resized = imutils.resize(self.original, width=640)

                            # Start permanent record or permanent screenshots
                            if self.is_record_permanent() and self.time_part_start == 0:
                                self.time_part_start = time.time()

                                if self.is_screenshots_mode():
                                    res = CameraStorage.take_screenshot(self.camera, self.original)
                                    Logger.debug(
                                        f"[Camera {self.camera.name}] Take screenshot: success={res.success}, fn={res.filename}, dir={res.directory}]")
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
                                        f'🎬 [{self.camera.name}] Permanent event start: #ID{self.permanent_event.id}]')

                                Logger.debug(
                                    f'📽 [{self.camera.name}] with permanent record mode: {self.camera.record_mode}')

                            # Take cover
                            now = time.time()
                            elapsed = now - self.screen_timer

                            if elapsed > self.screen_interval:
                                CameraStorage.upload_cover(self.camera, self.original)
                                self.screen_timer = now

                            # Write frames to output container if needed
                            with self._container_lock:
                                if self.output_container is not None and self.write:
                                    self.write_frame_safe(frame)
                                else:
                                    self.destroy_output_container()

                            pause = time.time() - self.silence_timer

                            if self.is_detection_mode() and (pause > self.silence_pause or first_run is True):
                                frame_copy = self.resized.copy()
                                changes = self.tracker.detect_changes(frame_copy, self.original)
                                __frame = self.tracker.draw_rois(frame_copy, changes)

                            elif self.is_record_permanent():
                                record_part_diff = time.time() - self.time_part_start
                                if record_part_diff > self.camera.record_duration * 60:
                                    self.destroy_output_container()
                                    Logger.debug(f'Camera {self.camera.name} end record video part')

                            first_run = False

            except EOFError as e:
                Logger.warn(f"⚠️ [{self.camera.name}] EOF reached, stream may be disconnected: {e}")
                self.need_restart = True
                time.sleep(1)  # Добавляем небольшую паузу перед следующей попыткой
                pass
            except av.error.FFmpegError as e:
                Logger.err(f"⚠️ [{self.camera.name}] FFmpegError: {e}")
                self.need_restart = True
                self.capture_error = True
                time.sleep(3)  # Увеличиваем паузу для серьезных ошибок
            except Exception as e:
                Logger.err(f"⚠️ [{self.camera.name}] Unexpected error: {e}")
                raise
                self.need_restart = True
                self.capture_error = True
                time.sleep(5)
        self.destroy_output_container()
        self.stop_input_container()
        self.output_container = None
        self.input_container = None
        Logger.warn(f'⛔️ [{self.camera.name}] stop stream')

    def _perform_restart(self):
        """Выполняет полный перезапуск потока"""
        Logger.debug(f"🔄 [{self.camera.name}] Performing full restart...")
        try:
            self.destroy_output_container()
            self.stop_input_container()
            self.create_input_container()
            self.last_frame_time = time.time()  # Сбрасываем таймер кадров
        except Exception as e:
            Logger.err(f"⚠️ [{self.camera.name}] Restart failed: {e}")
        finally:
            self.need_restart = False
            self.last_restart_time = time.time()

    def get_no_signal_frame(self):
        try:
            frame = cv2.imread(os.path.abspath('static/images/no-signal.jpg'))
            frame = imutils.resize(frame, width=640)
        except Exception:
            frame = np.zeros((640, 360, 1), dtype="uint8")
        return frame

    def generate_frames(self):
        time_prev = 0
        fps = 15

        while True:
            if self.input_container is None or self.resized is None:
                frame = self.get_no_signal_frame()
            else:
                frame = self.resized

            time_elapsed = time.time() - time_prev
            time_prev = time.time()

            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                continue

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

    def save_event(self):
        pass
