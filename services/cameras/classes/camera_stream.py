import datetime
import os
import time
from typing import TYPE_CHECKING, Optional, Union

import av
import imutils
import numpy as np
from av import VideoFrame
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


class ScreenshotResultModel(BaseModel):
    success: bool = False
    directory: str
    filename: str


class CameraStream:
    def __init__(self, camera: CameraEntity):
        self.id: int = 0
        self.tracker: Optional[ROITracker] = None
        self.opened: bool = True
        self.camera: Optional[CameraEntity] = None
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
        self.original: Optional[np.ndarray] = None
        self.resized: Optional[np.ndarray] = None

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
        self.write: bool = False

        # Error handling
        self.capture_error: Optional[bool] = None
        self.output_file: Optional[str] = None
        self.need_skip: bool = False

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
        return f'{proto.lower()}://{userinfo}{camera.ip}:{port}/{stream}'

    def set_camera(self, camera: CameraEntity):
        self.need_skip = True

        if isinstance(self.camera, CameraEntity) and camera != self.camera:
            self.destroy_output_container()
            self.stop_input_container()
            time.sleep(2)
            Logger.warn(f'{self.camera.name} url was changed! Capture should be reload')

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
            self.input_container = av.open(self.link, options=options)
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

    def destroy_output_container(self):
        if self.output_container is not None:
            # Flush any remaining packets
            if self.output_stream is not None:
                for packet in self.output_stream.encode():
                    self.output_container.mux(packet)

            # Также флашим аудиопакеты, если есть аудиопоток
            if hasattr(self, 'audio_output_stream') and self.audio_output_stream is not None:
                for packet in self.audio_output_stream.encode():
                    self.output_container.mux(packet)

            self.output_container.close()
            Logger.debug(f"🔳️ [{self.camera.name}] Output container stopped: {self.output_file}")
            self.output_container = None
            self.output_stream = None
            self.audio_output_stream = None  # Добавлено
            self.output_file = None

    def create_output_container(self, path: str):
        if not Filesystem.exists(path):
            Filesystem.mkdir(path, recursive=True)

        filename = f"{self.date_filename()}.mp4"
        full_path = os.path.join(path, filename)

        try:
            # Create output container
            self.output_container = av.open(full_path, mode='w')

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

    def loop_frames(self):
        first_run: bool = True
        need_create_input = False

        if self.input_container is None:
            need_create_input = True

        if need_create_input:
            self.create_input_container()

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
                if self.need_skip:
                    continue

                if self.input_container is None:
                    self.create_input_container()
                    continue

                # Читаем пакеты вместо фреймов для лучшей синхронизации
                for packet in self.input_container.demux():
                    if not self.camera.active and not self.opened:
                        break

                    if self.need_skip:
                        continue

                    # Демультиплексируем пакеты в фреймы
                    for frame in packet.decode():
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

                                Logger.debug(
                                    f'📽 [{self.camera.name}] with permanent record mode: {self.camera.record_mode}')

                            # Take cover
                            now = time.time()
                            elapsed = now - self.screen_timer

                            if elapsed > self.screen_interval:
                                CameraStorage.upload_cover(self.camera, self.original)
                                self.screen_timer = now

                            # Write frames to output container if needed
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
                                    self.time_part_start = 0
                                    self.destroy_output_container()
                                    Logger.debug(f'Camera {self.camera.name} end record video part')

                            first_run = False

            except EOFError as e:
                Logger.warn(f"⚠️ [{self.camera.name}] EOF reached, stream may be disconnected: {e}")
                pass
            except Exception as e:
                Logger.err(f"⚠️ [{self.camera.name}] error processing frame: {e}")
                self.capture_error = True
                time.sleep(1)
                break

        self.destroy_output_container()
        self.stop_input_container()
        Logger.warn(f'⛔️ [{self.camera.name}] stop stream')

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
