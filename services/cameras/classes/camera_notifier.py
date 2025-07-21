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
from repositories.camera_events_repository import CameraEventsRepository

if TYPE_CHECKING:
    from entities.camera_event import CameraEventEntity
    from services.cameras.classes.camera_stream import CameraStream
    from services.cameras.classes.roi_tracker import ROIDetectionEvent, ROIRecordEvent, ROI


class CameraNotifier:
    """Класс для обработки и уведомлений о событиях с камер видеонаблюдения.
    Обеспечивает отправку уведомлений через WebSocket и логирование событий.
    Все операции выполняются в отдельных потоках для избежания блокировки основного потока.
    """

    events: list["CameraEventEntity"] = []

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
    def _find_alert_by_roi(roi: "ROI"):
        for event in CameraNotifier.events:
            if event.area_id == roi.id:
                return event

    @staticmethod
    def _on_motion_start(event: "ROIDetectionEvent", stream: "CameraStream"):
        """Отправляет уведомление о начале движения через WebSocket и логирует событие.

        Args:
            event (ROIDetectionEvent): Событие обнаружения движения
        """
        # Срабатывает только, если режим камеры - изображения определения движения
        try:
            if stream.is_screenshot_detection_mode():
                created_event = CameraEventsRepository.add_event(event)
                with db.get_separate_session() as sess:
                    screenshot = CameraStorage.take_detection_screenshot(created_event.camera, event.frame, 'R')
                    created_event.screenshot = os.path.join(screenshot.directory, screenshot.filename)

                    # Обновляем оригинал файла только если событие - скриншот движения
                    original = CameraStorage.take_detection_screenshot(created_event.camera, event.original, 'O')
                    created_event.file = os.path.join(original.directory, original.filename)

                    sess.add(created_event)
                    sess.commit()
                    sess.refresh(created_event)

                CameraNotifier.events.append(created_event)

                message = WebsocketMessageDetectionStart(
                    camera_id=created_event.camera.id,
                    message=f'[{created_event.camera.name}] Motion detected at {created_event.start}',
                )
                WebSockets.send_broadcast(message)

                Logger.debug(
                    f"[ID#{created_event.id}] Начало движения в {created_event.area.name}. Время: {created_event.start}")
        except Exception as e:
            Logger.err(f"Error adding motion event with message: {e}")

    @staticmethod
    def _on_motion_end(event: "ROIDetectionEvent", stream: "CameraStream"):
        """Отправляет уведомление об окончании движения через WebSocket и логирует событие.

        Args:
            event (ROIDetectionEvent): Событие окончания движения
        """
        found_event = CameraNotifier._find_alert_by_roi(event.roi)
        if found_event is not None:
            found_event.action = event.event
            CameraEventsRepository.update_event_end(found_event)

            message = WebsocketMessageDetectionEnd(
                camera_id=event.camera.id,
                message=f'[{event.camera.name}] Reset movement counter'
            )
            WebSockets.send_broadcast(message)

            Logger.debug(f"[ID#{found_event.id}] Конец движения в {event.roi.name}. Время: {found_event.end}")

            CameraNotifier.events.remove(found_event)

    @staticmethod
    def _on_recording_start(event: "ROIRecordEvent", stream: "CameraStream"):
        """Логирует факт начала записи с камеры.

        Args:
            event (ROIRecordEvent): Событие начала записи
        """
        if stream.is_video_detection_mode():
            created_event = CameraEventsRepository.add_event(event)

            stream.destroy_writer()
            stream.create_writer(CameraStorage.video_detections_path(stream.camera))

            with db.get_separate_session() as sess:
                screenshot = CameraStorage.take_detection_screenshot(created_event.camera, event.frame, 'R')
                created_event.screenshot = os.path.join(screenshot.directory, screenshot.filename)
                created_event.file = stream.writer_file
                sess.add(created_event)
                sess.commit()
                sess.refresh(created_event)

            CameraNotifier.events.append(created_event)

            Logger.debug(f"[{event.timestamp}] Начата запись с камеры {event.camera.name} в {event.timestamp}")

    @staticmethod
    def _on_recording_end(event: "ROIRecordEvent", stream: "CameraStream"):
        """Логирует факт окончания записи с камеры, включая продолжительность записи.

        Args:
            event (ROIRecordEvent): Событие окончания записи
        """
        if stream.is_video_detection_mode():
            for _event in CameraNotifier.events:
                if stream.writer_file == _event.file:
                    found_event = _event
                    if found_event is not None:
                        with db.get_separate_session() as sess:
                            found_event.action = event.event
                            CameraEventsRepository.update_event_end(found_event)
                            stream.destroy_writer()
                            sess.add(found_event)
                            sess.commit()
                            sess.refresh(found_event)
                            Logger.debug(
                                f"[{found_event.end}] Завершена запись с {event.camera.name}. Длительность: {event.duration:.2f} сек")

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
        Logger.debug(f"Запущен поток для обработки {target.__name__} (ID: {thread.native_id})")
