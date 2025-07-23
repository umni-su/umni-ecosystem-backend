import os
import traceback
from threading import Thread
from typing import Callable, Any, TYPE_CHECKING
import database.database as db

from classes.logger import Logger
from classes.storages.camera_storage import CameraStorage
from classes.websockets.messages.ws_message_detection import (
    WebsocketMessageDetectionStart,
    WebsocketMessageDetectionEnd
)
from classes.websockets.websockets import WebSockets
from entities.camera import CameraEntity
from entities.camera_area import CameraAreaEntity
from entities.camera_recording import CameraRecordingEntity
from entities.enums.camera_record_type_enum import CameraRecordTypeEnum
from entities.camera_event import CameraEventEntity
from services.cameras.classes.roi_tracker import ROIDetectionEvent, ROIRecordEvent, ROIEventType

if TYPE_CHECKING:
    from services.cameras.classes.camera_stream import CameraStream


class CameraNotifier:
    """Класс для обработки и уведомлений о событиях с камер видеонаблюдения.
    Обеспечивает отправку уведомлений через WebSocket и логирование событий.
    Все операции выполняются в отдельных потоках для избежания блокировки основного потока.
    """

    active_events: list[CameraEventEntity] = []
    active_recordings: list[CameraRecordingEntity] = []

    @staticmethod
    def _find_active_event(area_id: int):
        for event in CameraNotifier.active_events:
            if event.area_id == area_id:
                return event
        return None

    @staticmethod
    def _find_active_recording(camera_id: int):
        for record in CameraNotifier.active_recordings:
            if record.camera_id == camera_id:
                return record
        return None

    @staticmethod
    def handle_motion_start(event: "ROIDetectionEvent", stream: "CameraStream"):
        """Обрабатывает начало движения в зоне интереса (ROI).
        Запускает уведомление в отдельном потоке.

        Args:
            event (ROIDetectionEvent): Событие обнаружения движения
            stream: (CameraStream)
        """
        CameraNotifier._notify_in_thread(CameraNotifier._on_motion_start, event, stream)

    @staticmethod
    def handle_motion_end(event: "ROIDetectionEvent", stream: "CameraStream"):
        """Обрабатывает окончание движения в зоне интереса (ROI).
        Запускает уведомление в отдельном потоке.

        Args:
            event (ROIDetectionEvent): Событие окончания движения
            stream: (CameraStream)
        """
        CameraNotifier._notify_in_thread(CameraNotifier._on_motion_end, event, stream)

    @staticmethod
    def handle_recording_start(event: "ROIRecordEvent", stream: "CameraStream"):
        """Обрабатывает начало записи с камеры.
        Запускает уведомление в отдельном потоке.

        Args:
            event (ROIRecordEvent): Событие начала записи
            stream:
        """
        CameraNotifier._notify_in_thread(CameraNotifier._on_recording_start, event, stream)

    @staticmethod
    def handle_recording_end(event: "ROIRecordEvent", stream: "CameraStream"):
        """Обрабатывает окончание записи с камеры.
        Запускает уведомление в отдельном потоке.

        Args:
            event (ROIRecordEvent): Событие окончания записи
            stream: (CameraStream)
        """
        CameraNotifier._notify_in_thread(CameraNotifier._on_recording_end, event, stream)

    @staticmethod
    def _on_motion_start(event: "ROIDetectionEvent", stream: "CameraStream"):
        """Отправляет уведомление о начале движения через WebSocket и логирует событие.

        Args:
            event (ROIDetectionEvent): Событие обнаружения движения
        """
        with db.get_separate_session() as sess:
            camera = sess.get(CameraEntity, event.camera.id)
            area = sess.get(CameraAreaEntity, event.roi.id)
            if area is None:
                Logger.err(f"⚠️ [{camera.name}] area is None")
                return
            key = area.id

            # Если уже есть активное событие для этой ROI, не создаем новое
            founded_event = CameraNotifier._find_active_event(key)

            if founded_event is not None:
                return
            # Создаем новое событие начала движения
            event_entity = CameraEventEntity(
                camera=camera,
                area=area,
                start=event.timestamp,
                type=camera.record_mode,
                action=ROIEventType.MOTION_START
            )

            screenshot = CameraStorage.take_detection_screenshot(camera, event.frame, 'R')
            event_entity.resized = os.path.join(screenshot.directory, screenshot.filename)

            # Обновляем оригинал файла только если событие - скриншот движения
            original = CameraStorage.take_detection_screenshot(camera, event.original, 'O')
            event_entity.original = os.path.join(original.directory, original.filename)

            new_record: bool = False

            # Для режима записи связываем с сессией записи
            # if camera.record_mode == CameraRecordTypeEnum.DETECTION_VIDEO:
            #     founded_record = CameraNotifier._find_active_recording(event.camera.id)
            #     if founded_record is None:
            #         new_record = True
            #         recording = CameraRecordingEntity(
            #             camera_id=event.camera.id,
            #             start=event.timestamp
            #         )
            #         # sess.add(recording)
            #         if event_entity.recording is None:
            #             event_entity.recording = recording
            #         # Создаем поток записи движения
            #         stream.destroy_writer()
            #         stream.create_writer(CameraStorage.video_detections_path(stream.camera))
            #     else:
            #         event_entity.camera_recording_id = founded_record.id

            sess.add(event_entity)
            sess.commit()
            sess.refresh(event_entity)

            message = WebsocketMessageDetectionStart(
                camera_id=event_entity.camera.id,
                message=f'[{event_entity.camera.name}] Motion detected at {event_entity.start}',
            )
            WebSockets.send_broadcast(message)

            Logger.debug(
                f"👋 [{camera.name} EvID#{event_entity.id}] Начало движения в {event_entity.area.name}. Время: {event_entity.start}")
            # if new_record:
            # CameraNotifier.active_recordings.append(recording)
            CameraNotifier.active_events.append(event_entity)

    @staticmethod
    def _on_motion_end(event: "ROIDetectionEvent", stream: "CameraStream"):
        """Отправляет уведомление об окончании движения через WebSocket и логирует событие.

        Args:
            event (ROIDetectionEvent): Событие окончания движения
        """
        with db.get_separate_session() as sess:
            key = event.roi.id

            # Находим активное событие для завершения
            founded_event = CameraNotifier._find_active_event(key)
            if founded_event is None:
                return

            event_entity = sess.get(CameraEventEntity, founded_event.id)

            # Обновляем параметры завершения
            event_entity.action = ROIEventType.MOTION_END
            event_entity.end = event.timestamp
            event_entity.duration = (event.timestamp - event_entity.start).total_seconds()

            sess.add(event_entity)
            sess.commit()
            sess.refresh(event_entity)

            message = WebsocketMessageDetectionStart(
                camera_id=event_entity.camera.id,
                message=f'[{event_entity.camera.name}] Motion detected end at {event_entity.end}, duration: {event_entity.duration}',
            )
            WebSockets.send_broadcast(message)

            CameraNotifier.active_events.remove(founded_event)
            Logger.debug(
                f"👋 [{event_entity.camera.name} EvID#{event_entity.id}] Конец движения в {event_entity.area.name}. Время: {event_entity.end}")

    @staticmethod
    def _on_recording_start(event: "ROIRecordEvent", stream: "CameraStream"):
        """Логирует факт начала записи с камеры.

        Args:
            event (ROIRecordEvent): Событие начала записи
        """
        Logger.debug(f"[{event.timestamp}] Начата запись с камеры {event.camera.name} в {event.timestamp}")

    @staticmethod
    def _on_recording_end(event: "ROIRecordEvent", stream: "CameraStream"):
        """Логирует факт окончания записи с камеры, включая продолжительность записи.

        Args:
            event (ROIRecordEvent): Событие окончания записи
        """
        with db.get_separate_session() as sess:
            founded_record = CameraNotifier._find_active_recording(event.camera.id)
            if isinstance(founded_record, CameraRecordingEntity):
                recording = sess.merge(founded_record)
                recording = sess.get(CameraRecordingEntity, recording.id)
                recording.end = event.timestamp
                recording.duration = (event.timestamp - recording.start).total_seconds()
                recording.path = stream.writer_file

                # Завершаем все активные события для этой камеры
                # for key in list(CameraNotifier.active_events.keys()):
                #     if key[0] == event.camera.id:
                #         CameraNotifier.handle_motion_end(
                #             ROIDetectionEvent(
                #                 camera=event.camera,
                #                 roi=event.rois[0],  # Примерно, нужно адаптировать
                #                 timestamp=event.timestamp
                #             ),
                #             stream
                #         )

                sess.commit()
                CameraNotifier.active_recordings.remove(founded_record)
                Logger.debug(
                    f"[{recording.end}] Завершена запись с {event.camera.name}. Длительность: {recording.duration:.2f} сек")
                stream.destroy_writer()

    @staticmethod
    def _notify_in_thread(target: Callable, *args: Any, **kwargs: Any) -> None:
        """Запускает переданную функцию в отдельном потоке с обработкой исключений.

        Args:
            target (Callable): Функция для выполнения в потоке
            *args: Аргументы для целевой функции
            **kwargs: Именованные аргументы для целевой функции

        При возникновении ошибки логирует её с деталями.
        """

        def wrapped_target():
            try:
                # Если передан один аргумент и это кортеж - распаковываем его
                actual_args = args[0] if len(args) == 1 and isinstance(args[0], tuple) else args
                target(*actual_args, **kwargs)
            except Exception as e:
                error_msg = (
                    f"Ошибка в потоке уведомлений: {str(e)}\n"
                    f"Тип: {type(e).__name__}\n"
                    f"Целевая функция: {target.__name__}\n"
                    f"Аргументы: args={args}, kwargs={kwargs}\n"
                    f"Трейсбэк:\n{traceback.format_exc()}"
                )
                Logger.err(error_msg)

        thread = Thread(
            daemon=True,
            target=wrapped_target,
            name=f"CameraNotifierThread-{target.__name__}"  # Полезно для отладки
        )
        thread.start()
        Logger.debug(f"🐍 Запущен поток для обработки {target.__name__} (ID: {thread.native_id})")
