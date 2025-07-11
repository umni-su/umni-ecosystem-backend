import datetime
import os
import time

import imutils
import numpy as np

from classes.crypto.crypto import Crypto
from classes.logger import Logger
from classes.storages.camera_storage import CameraStorage
from classes.storages.filesystem import Filesystem
from classes.thread.Daemon import Daemon
from classes.websockets.messages.ws_message_detection import WebsocketMessageDetectionStart, \
    WebsocketMessageDetectionEnd
from classes.websockets.websockets import WebSockets
from entities.camera import CameraEntity
import cv2

from entities.enums.camera_record_type_enum import CameraRecordTypeEnum


class CameraStream:
    id: int
    opened: bool = True
    camera: CameraEntity
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
        self.prepare_link(camera=camera)
        self.set_camera(camera=camera)
        self.try_capture()
        self.path = os.path.join(self.camera.storage.path, str(self.camera.id))

    @staticmethod
    def prepare_link(camera: CameraEntity, secondary: bool = False):
        userinfo = ''
        if camera.username is not None and camera.password is not None:
            password = Crypto.decrypt(camera.password)
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
        url = f'{proto.lower()}://{userinfo}{camera.ip}:{port}/{stream}'
        CameraStream.link = url

    def set_camera(self, camera: CameraEntity):
        # stop writer
        self.camera = camera
        self.id = camera.id

    def date_filename(self):
        return datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')

    def take_screenshot(self, path: str) -> bool:
        filename = '.'.join([self.date_filename(), 'jpg'])
        if not Filesystem.exists(path):
            Filesystem.mkdir(path_or_filename=path, recursive=True)
        full_filename = os.path.join(path, filename)
        return cv2.imwrite(
            filename=full_filename,
            img=self.original
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
                self.cap = cv2.VideoCapture(self.link)
                # self.cap = cv2.VideoCapture(0)
                Logger.info(f'[{self.camera.name}] Create capture on link {self.link}')

            elif not self.cap.isOpened():
                self.cap = cv2.VideoCapture(self.link)
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

    def create_writer(self, path: str):
        # Get frame width and height
        frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(self.cap.get(cv2.CAP_PROP_FPS))

        # Define the codec and create VideoWriter object
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        if not Filesystem.exists(path):
            Filesystem.mkdir(path)
        filename = '.'.join([
            self.date_filename(), 'mp4'
        ])
        full_path = os.path.join(
            path,
            filename
        )
        self.writer = cv2.VideoWriter(full_path, fourcc, fps, (frame_width, frame_height))

    def loop_frames(self):
        first_run: bool = True
        while self.camera.active or self.opened:
            if self.silence_timer is 0:
                self.silence_timer = time.time()
            # Set transient motion detected as false
            self.transient_movement_flag = False
            # Read frame
            ret, frame = self.cap.read()
            # If there's an error in capturing
            if not ret:
                Logger.err(f"Camera {self.camera.name} capture error!")
                continue

            self.original = frame

            if self.is_record_permanent() and self.time_part_start == 0:
                self.time_part_start = time.time()
                # If mode is screenshot
                if self.is_screenshots_mode():
                    # take motion detection screenshot
                    self.take_screenshot(CameraStorage.screenshots_path(self.camera))
                # If mode is video
                elif self.is_video_mode():
                    self.destroy_writer()
                    # Create video writer
                    self.create_writer(CameraStorage.video_path(self.camera))
                Logger.debug(f'Camera {self.camera.name} with permanent record mode: {self.camera.record_mode}')

            now = time.time()
            elapsed = now - self.screen_timer

            if elapsed > self.screen_interval:
                CameraStorage.upload_cover(self.camera, self.original)
                self.screen_timer = now
            # Resize and save a greyscale version of the image
            self.resized = imutils.resize(self.original, width=450)

            # If writer is opened - write frames to storage
            if isinstance(self.writer, cv2.VideoWriter):
                if self.writer.isOpened():
                    self.writer.write(self.original)

            pause = time.time() - self.silence_timer
            if self.is_detection_mode() and (pause > self.silence_pause or first_run is True):
                first_run = False
                # Detection start
                gray = cv2.cvtColor(self.resized, cv2.COLOR_BGR2GRAY)
                # Blur it to remove camera noise (reducing false positives)
                gray = cv2.GaussianBlur(gray, (21, 21), 0)
                # If the first frame is nothing, initialise it
                if self.first_frame is None:
                    self.first_frame = gray
                self.delay_counter += 1
                # Otherwise, set the first frame to compare as the previous frame
                # But only if the counter reaches the appriopriate value
                # The delay is to allow relatively slow motions to be counted as large
                # motions if they're spread out far enough
                if self.delay_counter > self.frames_skip:
                    self.delay_counter = 0
                    self.first_frame = self.next_frame
                # Set the next frame to compare (the current frame)
                self.next_frame = gray
                # Compare the two frames, find the difference
                frame_delta = cv2.absdiff(self.first_frame, self.next_frame)
                thresh: cv2.Mat | int | np.ndarray | None = cv2.threshold(frame_delta, 50, 255, cv2.THRESH_BINARY)[1]
                # Fill in holes via dilate(), and find contours of the thesholds
                thresh = cv2.dilate(thresh, None, iterations=2)
                cnts, _ = cv2.findContours(
                    image=thresh.copy(),
                    mode=cv2.RETR_EXTERNAL,
                    method=cv2.CHAIN_APPROX_SIMPLE
                )
                # loop over the contours
                for c in cnts:
                    # Save the coordinates of all found contours
                    (x, y, w, h) = cv2.boundingRect(c)
                    # If the contour is too small, ignore it, otherwise, there's transient
                    # movement
                    # TODO учет пропорций ширины и высоты
                    if cv2.contourArea(c) > self.detection_size and (w / h > 0.9 or h / w > 0.9):
                        self.transient_movement_flag = True
                        # Draw a rectangle around big enough movements
                        cv2.rectangle(self.resized, (x, y), (x + w, y + h), (0, 255, 0), 2)
                # The moment something moves momentarily, reset the persistent
                # movement timer.
                if self.transient_movement_flag is True:
                    self.movement_persistent_flag = True
                    self.movement_persistent_counter = self.detection_persistent
                # As long as there was a recent transient movement, say a movement
                # was detected
                if self.movement_persistent_counter > 0:
                    if not self.movement_detected:
                        self.movement_detected = True
                        # motion was detected, if record_mode was given, start record
                        if self.camera.record_mode == CameraRecordTypeEnum.DETECTION_VIDEO:
                            # Start VideoWriter
                            self.create_writer(CameraStorage.video_detections_path(self.camera))
                        elif self.camera.record_mode == CameraRecordTypeEnum.DETECTION_SCREENSHOTS:
                            # Save only screenshot
                            self.take_screenshot(CameraStorage.screenshots_detections_path(self.camera))
                        message = WebsocketMessageDetectionStart(
                            camera_id=self.camera.id,
                            message=f'[{self.camera.name}] Motion detected at {datetime.datetime.now()}',
                        )
                        Logger.warn(message.message)
                        WebSockets.send_broadcast(message)
                    self.movement_persistent_counter -= 1
                else:
                    if self.movement_detected:
                        self.movement_detected = False
                        message = WebsocketMessageDetectionEnd(
                            camera_id=self.camera.id,
                            message=f'[{self.camera.name}] Reset movement counter'
                        )
                        # Stop writer
                        self.destroy_writer()
                        Logger.warn(message.message)
                        WebSockets.send_broadcast(message)

                        self.silence_timer = 0
                # Detection end

            elif self.is_record_permanent():
                record_part_diff = time.time() - self.time_part_start
                if record_part_diff > self.camera.record_duration * 60:
                    self.time_part_start = 0
                    self.destroy_writer()
                    Logger.debug(f'Camera {self.camera.name} end record video part')
                # text = "No Movement Detected"

        # Cleanup when closed
        cv2.waitKey(10)
        # cv2.destroyAllWindows()
        # if isinstance(self.cap, cv2.VideoCapture):
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
