import datetime
import os
import time
from typing import TYPE_CHECKING

import imutils
import numpy as np
from numpy import ndarray
from pydantic import BaseModel

import classes.crypto.crypto as crypto
from classes.logger import Logger
from classes.storages.camera_storage import CameraStorage
from classes.storages.filesystem import Filesystem
from classes.thread.Daemon import Daemon
from entities.camera import CameraEntity
import cv2

from entities.enums.camera_record_type_enum import CameraRecordTypeEnum
from services.cameras.classes.camera_notifier import CameraNotifier
from services.cameras.classes.roi_tracker import ROIDetectionEvent

from services.cameras.classes.roi_tracker import ROITracker

if TYPE_CHECKING:
    from services.cameras.classes.roi_tracker import ROIRecordEvent

os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
    "transport_protocol;tcp"
    "video_codec;h264"
)
os.environ["OPENCV_FFMPEG_LOGLEVEL"] = "debug"  # Вывод подробных логов


class ScreenshotResultModel(BaseModel):
    success: bool = False
    directory: str
    filename: str


class CameraStream:
    id: int
    tracker: ROITracker | None = None
    opened: bool = True
    camera: CameraEntity | None = None
    cap: cv2.VideoCapture | None = None
    link: str | int | None = None
    # Number of frames to pass before changing the frame to compare the current
    # frame against
    frames_skip: int = 20
    # Minimum boxed area for a detected motion to count as actual motion
    # Use to filter out noise or small objects
    detection_size: int = 5000
    # Minimum length of time where no motion is detected it should take
    # (in program cycles) for the program to declare that there is no movement
    detection_persistent: int = 100
    # Silence timer
    silence_timer: int | float = 0
    # No detect movement after 10 seconds after previous detection was detected
    silence_pause: int = 10

    cap: cv2.VideoCapture
    font = cv2.FONT_HERSHEY_SIMPLEX
    delay_counter = 0
    movement_persistent_counter = 0
    first_frame: None | cv2.Mat = None
    next_frame: None | cv2.Mat = None
    fps: int = 10

    time_part_start: int | float = 0

    time_prev: int | float = 0
    time_elapsed: int | float = 0

    original: cv2.typing.MatLike = None
    resized: cv2.typing.MatLike = None
    daemon: Daemon | None = None
    transient_movement_flag: bool = False
    movement_persistent_flag: bool = False
    movement_detected: bool = False
    path: str
    screen_interval: int = 30
    screen_timer: float = 0
    path: str | None = None

    writer: cv2.VideoWriter | None = None

    need_skip: bool = False

    def __init__(self, camera: CameraEntity):
        self.capture_error = None
        self.writer_file: str | None = None
        self.set_camera(camera=camera)  # -> capture creates here

        dmn = 'was_undefined'
        if isinstance(self.daemon, Daemon):
            if not self.daemon.thread.is_alive():
                self.daemon.thread = None
                self.daemon = None
                dmn = 'was_dead'

        if self.daemon is None:
            self.daemon = Daemon(self.loop_frames)
            Logger.debug(f"👻 [{self.camera.name}] Daemon was created, reason={dmn}")

    def handle_motion_start(self, event: "ROIDetectionEvent"):
        CameraNotifier.handle_motion_start(event, self)

    def handle_motion_end(self, event: "ROIDetectionEvent"):
        CameraNotifier.handle_motion_end(event, self)

    def handle_recording_start(self, event: "ROIRecordEvent"):
        CameraNotifier.handle_recording_start(event, self)

    def handle_recording_end(self, event: "ROIRecordEvent"):
        CameraNotifier.handle_recording_end(event, self)

    def prepare_link(self, camera: CameraEntity, secondary: bool = False):
        userinfo = ''
        if camera.username is not None and camera.password is not None:
            password = crypto.Crypto.decrypt(camera.password)
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
        url = (
            f'{proto.lower()}://{userinfo}{camera.ip}:{port}/{stream}'
            # "?transport=tcp&"
            # "buffer_size=4194304&"  # Увеличение до 4 МБ (для 4K потоков)
            # "analyzeduration=20000000&"  # 20 сек анализа для сложных потоков
            # "probesize=20000000&"  # Максимальный анализ
            # "fflags=+genpts+discardcorrupt+nobuffer+flush_packets&"
            # "flags=+low_delay+autobsf&"  # Автоматическая битстрим-фильтрация
            # "strict=experimental&"
            # "use_wallclock_as_timestamps=1&"
            # "skip_loop_filter=all&"
            # "reconnect_at_eof=1&"
            # "reconnect_streamed=1&"
            # "reconnect_delay_max=5&"
            # "timeout=5000000&"  # Таймаут 5 сек
            # "max_delay=500000"  # Максимальная задержка пакетов
        )
        return url

    def set_camera(self, camera: CameraEntity):
        self.need_skip = True

        if isinstance(self.camera, CameraEntity):
            if camera != self.camera:
                # camera url update
                # stop capture
                # recreate capture
                self.destroy_writer()
                self.stop_capture()
                time.sleep(2)
                Logger.warn(f'{self.camera.name} url was changed! Capture should be reload')

        self.camera = camera
        self.id = self.camera.id
        self.link = self.prepare_link(self.camera)
        self.path = os.path.join(self.camera.storage.path, str(self.camera.id))

        if self.camera.record_mode != camera.record_mode:
            # Stop writer
            self.destroy_writer()
            self.time_part_start = 0

        if isinstance(self.tracker, ROITracker):
            self.tracker.update_all_rois(self.camera.areas)

        self.need_skip = False

    def date_filename(self):
        return datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')

    def take_screenshot(self, path: str, prefix: str | None = None, frame: cv2.Mat | ndarray | None = None):

        filename = '.'.join([self.date_filename(), 'jpg'])
        if prefix is not None:
            filename = '.'.join([prefix, filename])

        if not Filesystem.exists(path):
            Filesystem.mkdir(path_or_filename=path, recursive=True)
        full_filename = os.path.join(path, filename)
        _frame = self.original
        if frame is not None:
            _frame = frame
        res = cv2.imwrite(
            filename=full_filename,
            img=frame
        )
        return ScreenshotResultModel(
            success=res,
            directory=path,
            filename=filename,
        )

    def _create_video_stream(self):
        self.cap = cv2.VideoCapture(self.link, cv2.CAP_FFMPEG)
        if not self.cap.isOpened():
            self.capture_error = True
            Logger.debug(
                f"⚠️ [{self.camera.name}] Restart camera capture on error {self.link}")
            time.sleep(3)
            self._create_video_stream()

    def create_capture(self):
        if self.cap is None or (isinstance(self.cap, cv2.VideoCapture) and not self.cap.isOpened()):
            self._create_video_stream()

            self.capture_error = False
            # Настройки таймаутов
            self.cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
            self.cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 10000)
            # self.cap = cv2.VideoCapture(0)

            Logger.debug(f"🎉 [{self.camera.name}] Start capture on link {self.link}")
            self.capture_error = False

    def stop_capture(self):
        if isinstance(self.cap, cv2.VideoCapture):
            self.cap.release()
            cv2.waitKey(10)
            # cv2.destroyWindow(f"Camera {self.camera.id}")

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

    def write_frame_safe(self):
        if (
                self.writer is None
                or not self.writer.isOpened()
                or self.original is None
        ):
            return False

        try:
            # Проверяем размер кадра
            self.writer.write(self.original)
            return True

        except cv2.error as e:
            Logger.err(f"[{self.camera.name}] OpenCV Writer Error: {e}")
            self.destroy_writer()
            return False

        except Exception as e:
            Logger.err(f"[{self.camera.name}] Unexpected Writer Error: {e}")
            self.destroy_writer()
            return False

    def destroy_writer(self):
        if isinstance(self.writer, cv2.VideoWriter):
            self.writer.release()
            Logger.debug(f"🔳️ [{self.camera.name}] VideoWriter stopped: {self.writer_file}")
            self.writer = None
            self.writer_file = None

    def create_writer(self, path: str):
        if not Filesystem.exists(path):
            Filesystem.mkdir(path, recursive=True)

        # Получаем параметры кадра (если cap доступен)
        frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)) if self.cap.isOpened() else 0
        frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) if self.cap.isOpened() else 0
        fps = int(self.cap.get(cv2.CAP_PROP_FPS)) if self.cap.isOpened() else 25

        # Если размеры не получены, берём из первого кадра
        if frame_width <= 0 or frame_height <= 0:
            if self.original is not None:
                frame_height, frame_width = self.original.shape[:2]
            else:
                frame_width, frame_height = 640, 480  # Fallback

        # Выбираем кодек (XVID работает почти везде)
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        filename = f"{self.date_filename()}.avi"  # .avi для XVID
        full_path = os.path.join(path, filename)

        # Создаём VideoWriter
        self.writer = cv2.VideoWriter(
            full_path,
            fourcc,
            fps,
            (frame_width, frame_height)
        )

        if not self.writer.isOpened():
            Logger.err(f"[{self.camera.name}] Failed to initialize VideoWriter!")
            self.writer = None
            return False

        self.writer_file = full_path
        Logger.debug(f"[{self.camera.name}] VideoWriter started: {full_path}")
        return True

    def loop_frames(self):
        first_run: bool = True
        need_create_capture = False
        if self.cap is None:
            need_create_capture = True
        elif not self.cap.isOpened():
            need_create_capture = True
        if need_create_capture:
            self.create_capture()
        self.tracker = ROITracker(camera=self.camera)
        # Установка callback-функций
        self.tracker.set_callbacks(
            motion_start=self.handle_motion_start,
            motion_end=self.handle_motion_end,
            recording_start=self.handle_recording_start,
            recording_end=self.handle_recording_end
        )
        while self.camera.active or self.opened:
            # Read frame
            try:
                if self.need_skip:
                    continue

                if not self.cap.isOpened():
                    self.create_capture()

                ret, frame = self.cap.read()

                # If there's an error in capturing
                if not ret:
                    Logger.err(f"⚠️ [{self.camera.name}] capture error!")
                    self.capture_error = True
                    self.opened = False
                    break
                else:
                    self.capture_error = False
                    self.original = frame
                    self.resized = imutils.resize(self.original, width=640)

                    # Start permanent record or permanent screenshots
                    if self.is_record_permanent() and self.time_part_start == 0:
                        self.time_part_start = time.time()
                        # If mode is screenshot
                        if self.is_screenshots_mode():
                            # take motion detection screenshot
                            res = CameraStorage.take_screenshot(self.camera, self.original)
                            Logger.debug(
                                f"[Camera {self.camera.name}] Take screenshot: success={res.success}, fn={res.filename}, dir={res.directory}]")
                        # If mode is video
                        elif self.is_video_mode() and self.writer is None:
                            # Create video writer
                            self.create_writer(CameraStorage.video_path(self.camera))
                        Logger.debug(
                            f'📽 [{self.camera.name}] with permanent record mode: {self.camera.record_mode}')

                    # Take cover
                    now = time.time()
                    elapsed = now - self.screen_timer

                    if elapsed > self.screen_interval:
                        CameraStorage.upload_cover(self.camera, self.original)
                        self.screen_timer = now
                    # End take cover

                    # If writer is opened - write frames to storage
                    if self.writer is not None:
                        self.write_frame_safe()

                    pause = time.time() - self.silence_timer

                    if self.is_detection_mode() and (pause > self.silence_pause or first_run is True):

                        frame_copy = self.resized.copy()

                        changes = self.tracker.detect_changes(frame_copy, self.original)
                        __frame = self.tracker.draw_rois(frame_copy, changes)
                        # cv2.imshow(f"Camera {self.camera.id}", __frame)

                    elif self.is_record_permanent():
                        record_part_diff = time.time() - self.time_part_start
                        # cv2.imshow(f"Camera {self.camera.id}", self.resized)
                        if record_part_diff > self.camera.record_duration * 60:
                            self.time_part_start = 0
                            self.destroy_writer()
                            Logger.debug(f'Camera {self.camera.name} end record video part')
                        # text = "No Movement Detected"

                    cv2.waitKey(5)

            except cv2.error as e:
                Logger.err(f"⚠️ [{self.camera.name}] error read frame: {e}")
                break

        self.destroy_writer()
        self.stop_capture()
        Logger.warn(f'⛔️ [{self.camera.name}] stop stream')

    '''
    
    '''

    def get_no_signal_frame(self):
        try:
            frame = cv2.imread(os.path.abspath('static/images/no-signal.jpg'))
            frame = imutils.resize(frame, width=640)
        except cv2.error as e:
            frame = np.zeros((640, 360, 1), dtype="uint8")
        return frame

    '''
    Generate videoframes stream to view
    '''

    def generate_frames(self):
        time_prev = 0
        fps = 15

        while True:
            cap = self.cap
            if not isinstance(cap, cv2.VideoCapture):
                frame = self.get_no_signal_frame()
            elif not cap.isOpened():
                frame = self.get_no_signal_frame()
            elif self.resized is None:
                frame = self.get_no_signal_frame()
            else:
                frame = self.resized
            time_elapsed = time.time() - time_prev
            # if time_elapsed > 1. / fps:
            time_prev = time.time()
            # Process the frame with OpenCV (optional)
            # processed_frame = your_opencv_processing_function(frame)

            ret, buffer = cv2.imencode('.jpg', frame)  # Encode frame as JPEG
            if not ret:
                continue

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            # continue

    def save_event(self):
        pass
