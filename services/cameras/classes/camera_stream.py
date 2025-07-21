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

    writer: cv2.VideoWriter | None = None

    def __init__(self, camera: CameraEntity):
        self.writer_file: str | None = None
        self.prepare_link(camera=camera)
        self.set_camera(camera=camera)
        self.try_capture()
        self.path = os.path.join(self.camera.storage.path, str(self.camera.id))

    def handle_motion_start(self, event: "ROIDetectionEvent"):
        CameraNotifier.handle_motion_start(event, self)

    def handle_motion_end(self, event: "ROIDetectionEvent"):
        CameraNotifier.handle_motion_end(event, self)

    def handle_recording_start(self, event: "ROIRecordEvent"):
        CameraNotifier.handle_recording_start(event, self)

    def handle_recording_end(self, event: "ROIRecordEvent"):
        CameraNotifier.handle_recording_end(event, self)

    @staticmethod
    def prepare_link(camera: CameraEntity, secondary: bool = False):
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
            "?transport=tcp&"
            "buffer_size=4194304&"  # Увеличение до 4 МБ (для 4K потоков)
            "analyzeduration=20000000&"  # 20 сек анализа для сложных потоков
            "probesize=20000000&"  # Максимальный анализ
            "fflags=+genpts+discardcorrupt+nobuffer+flush_packets&"
            "flags=+low_delay+autobsf&"  # Автоматическая битстрим-фильтрация
            "strict=experimental&"
            "use_wallclock_as_timestamps=1&"
            "skip_loop_filter=all&"
            "reconnect_at_eof=1&"
            "reconnect_streamed=1&"
            "reconnect_delay_max=5&"
            "timeout=5000000&"  # Таймаут 5 сек
            "max_delay=500000"  # Максимальная задержка пакетов
        )
        CameraStream.link = url

    def set_camera(self, camera: CameraEntity):
        if isinstance(self.camera, CameraEntity):
            if self.link != self.prepare_link(
                    camera=camera,
                    secondary=False
            ):
                # camera url update
                # stop capture
                # recreate capture
                pass
            if self.camera.record_mode != camera.record_mode:
                # Stop writer
                self.destroy_writer()
                self.time_part_start = 0

        self.camera = camera
        self.id = camera.id

        if isinstance(self.tracker, ROITracker):
            self.tracker.update_all_rois(self.camera.areas)

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

    def try_capture(self):
        if self.camera.active:
            self.create_capture()
            while not self.cap.isOpened():
                self.cap.release()
                self.create_capture()
                Logger.err('Retrying in 3 seconds...')
                time.sleep(3)
            if self.daemon is None:
                self.daemon = Daemon(self.loop_frames)
        return self

    def create_capture(self):
        if not self.camera.active:
            self.stop_capture()
        else:
            if self.cap is None:
                self.cap = cv2.VideoCapture(self.link, cv2.CAP_FFMPEG)
                # Настройки таймаутов
                self.cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
                self.cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 10000)
                # self.cap = cv2.VideoCapture(0)
                Logger.info(f'[{self.camera.name}] Create capture on link {self.link}')

            elif not self.cap.isOpened():
                self.cap.release()
                self.cap = cv2.VideoCapture(self.link, cv2.CAP_FFMPEG)
                self.destroy_writer()
                self.daemon = None
                Logger.info(f'[{self.camera.name}] Restart capture')

    def stop_capture(self):
        if isinstance(self.cap, cv2.VideoCapture):
            self.cap.release()

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

    def destroy_writer(self):
        if isinstance(self.writer, cv2.VideoWriter):
            self.writer.release()
            self.writer = None
            self.writer_file = None

    def create_writer(self, path: str):
        # Get frame width and height
        frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(self.cap.get(cv2.CAP_PROP_FPS))

        # Define the codec and create VideoWriter object
        # fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        if not Filesystem.exists(path):
            Filesystem.mkdir(path)
        filename = '.'.join([
            self.date_filename(), 'mkv'
        ])
        full_path = os.path.join(
            path,
            filename
        )
        self.writer_file = full_path
        self.writer = cv2.VideoWriter(full_path, fourcc, fps, (frame_width, frame_height))

    def loop_frames(self):
        first_run: bool = True
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
            ret: bool = False
            frame: ndarray | cv2.Mat = None
            for _ in range(5):  # Пробуем несколько раз
                ret, frame = self.cap.read()
                if ret: break

            # If there's an error in capturing
            if not ret:
                Logger.err(f"Camera {self.camera.name} capture error!")
                self.destroy_writer()
                self.cap.release()
                time.sleep(2)
                self.try_capture()

                for _ in range(5):  # Пробуем несколько раз
                    ret, frame = self.cap.read()
                    if ret: break

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
                elif self.is_video_mode():
                    # Create video writer
                    self.create_writer(CameraStorage.video_path(self.camera))
                Logger.debug(f'Camera {self.camera.name} with permanent record mode: {self.camera.record_mode}')

            # Take cover
            now = time.time()
            elapsed = now - self.screen_timer

            if elapsed > self.screen_interval:
                CameraStorage.upload_cover(self.camera, self.original)
                self.screen_timer = now
            # End take cover

            # If writer is opened - write frames to storage
            if isinstance(self.writer, cv2.VideoWriter):
                if self.writer.isOpened():
                    try:
                        self.writer.write(self.original)
                    except Exception as e:
                        self.destroy_writer()
                        self.cap.release()
                        Logger.err(e)

            pause = time.time() - self.silence_timer

            if self.is_detection_mode() and (pause > self.silence_pause or first_run is True):

                frame_copy = self.resized.copy()

                changes = self.tracker.detect_changes(frame_copy, self.original)
                __frame = self.tracker.draw_rois(frame_copy, changes)
                cv2.imshow(f"Camera {self.camera.id}", __frame)

            elif self.is_record_permanent():
                record_part_diff = time.time() - self.time_part_start
                cv2.imshow(f"Camera {self.camera.id}", self.resized)
                if record_part_diff > self.camera.record_duration * 60:
                    self.time_part_start = 0
                    self.destroy_writer()
                    Logger.debug(f'Camera {self.camera.name} end record video part')
                # text = "No Movement Detected"

            cv2.waitKey(3)

        # Restart capture on error
        if self.camera.active:
            time.sleep(1)
            self.try_capture()
        cv2.destroyAllWindows()
        self.destroy_writer()
        self.stop_capture()
        Logger.warn(f'[{self.camera.name}] Stop stream')

    def generate_frames(self):
        cap = self.cap
        if not isinstance(cap, cv2.VideoCapture):
            Logger.err(f'Camera {self.camera.name} cap is not open')
            return
        if not cap.isOpened():
            Logger.err(f"Camera {self.camera.name} could not open RTSP stream.")
            return
        time_prev = 0
        fps = 15

        while True:
            time_elapsed = time.time() - time_prev
            # if time_elapsed > 1. / fps:
            time_prev = time.time()
            # Process the frame with OpenCV (optional)
            # processed_frame = your_opencv_processing_function(frame)

            ret, buffer = cv2.imencode('.jpg', self.resized)  # Encode frame as JPEG
            if not ret:
                continue

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            # continue

    def save_event(self):
        pass
