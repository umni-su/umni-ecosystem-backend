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

import os
import traceback
from threading import Thread
from typing import Callable, Any, TYPE_CHECKING

from classes.events.event_bus import event_bus
from classes.events.event_types import EventType
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from classes.storages.camera_storage import CameraStorage
from classes.websockets.messages.ws_message_detection import (
    WebsocketMessageDetectionStart,
    WebsocketMessageDetectionEnd
)
from classes.websockets.websockets import WebSockets
from database.session import write_session

from entities.camera_area import CameraAreaEntity
from entities.camera_recording import CameraRecordingEntity
from entities.enums.camera_record_type_enum import CameraRecordTypeEnum
from entities.camera_event import CameraEventEntity
from models.camera_event_model import CameraEventBaseModel
from models.camera_recording import CameraRecordingModel
from models.enums.log_code import LogCode
from models.log_model import LogEntityCode

from services.cameras.classes.roi_tracker import ROIDetectionEvent, ROIRecordEvent, ROIEventType

if TYPE_CHECKING:
    from services.cameras.classes.camera_stream import CameraStream


class CameraNotifier:
    """Класс для обработки и уведомлений о событиях с камер видеонаблюдения.
    Обеспечивает отправку уведомлений через WebSocket и логирование событий.
    Все операции выполняются в отдельных потоках для избежания блокировки основного потока.
    """

    active_events: list[CameraEventBaseModel] = []
    active_recordings: list[CameraRecordingModel] = []

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
        with write_session() as sess:
            # camera = sess.get(CameraEntity, event.camera.id)
            area = sess.get(CameraAreaEntity, event.roi.id)
            if area is None:
                Logger.err(f"⚠️ [{event.camera.name}] area is None", LoggerType.CAMERAS)
                return
            key = area.id

            # Если уже есть активное событие для этой ROI, не создаем новое
            founded_event = CameraNotifier._find_active_event(key)

            if founded_event is not None:
                return
            # Создаем новое событие начала движения
            event_entity = CameraEventEntity(
                camera_id=event.camera.id,
                area=area,
                start=event.timestamp,
                type=event.camera.record_mode.value,
                action=ROIEventType.MOTION_START.value
            )

            screenshot = CameraStorage.take_detection_screenshot(event.camera, event.frame, 'R')
            event_entity.resized = os.path.join(screenshot.directory, screenshot.filename)

            # Обновляем оригинал файла только если событие - скриншот движения
            original = CameraStorage.take_detection_screenshot(event.camera, event.original, 'O')
            event_entity.original = os.path.join(original.directory, original.filename)

            new_record: bool = False
            recording = None

            # Для режима записи связываем с сессией записи
            if event.camera.record_mode == CameraRecordTypeEnum.DETECTION_VIDEO:
                founded_record = CameraNotifier._find_active_recording(event.camera.id)
                if founded_record is None:
                    new_record = True

                    recording = CameraRecordingEntity(
                        camera_id=event.camera.id,
                        start=event.timestamp
                    )
                    # sess.add(recording)
                    if event_entity.recording is None:
                        event_entity.recording = recording
                    # Создаем поток записи движения
                    stream.destroy_output_container()
                    stream.create_output_container(CameraStorage.video_detections_path(stream.camera))
                else:
                    event_entity.camera_recording_id = founded_record.id

            sess.add(event_entity)
            sess.commit()
            sess.refresh(event_entity)

            event_model = CameraEventBaseModel.model_validate(
                event_entity.to_dict(
                    include_relationships=True
                )
            )

            message = WebsocketMessageDetectionStart(
                camera_id=event_model.camera.id,
                area_id=event_model.area.id,
                message=f'[{event_entity.camera.name}] Motion detected at {event_model.start}',
            )
            WebSockets.send_broadcast(message)

            Logger.debug(
                f"👋 [{event.camera.name} EvID#{event_model.id}] Начало движения в {event_model.area.name}. Время: {event_model.start}",
                LoggerType.CAMERAS,
                with_db=True,
                entity_code=LogEntityCode(
                    id=event.camera.id,
                    code=LogCode.CAMERA_MOTION_START
                )
            )
            if new_record and recording is not None:
                recording_model = CameraRecordingModel.model_validate(
                    recording.to_dict()
                )
                CameraNotifier.active_recordings.append(recording_model)
            CameraNotifier.active_events.append(event_model)

            # Publish motion start event
            event_bus.publish(EventType.MOTION_START, event=event_model)

    @staticmethod
    def _on_motion_end(event: "ROIDetectionEvent", stream: "CameraStream"):
        """Отправляет уведомление об окончании движения через WebSocket и логирует событие.

        Args:
            event (ROIDetectionEvent): Событие окончания движения
        """
        with write_session() as sess:
            key = event.roi.id

            # Находим активное событие для завершения
            founded_event = CameraNotifier._find_active_event(key)
            if founded_event is None:
                return

            event_entity = sess.get(CameraEventEntity, founded_event.id)

            # Обновляем параметры завершения
            event_entity.action = ROIEventType.MOTION_END.value
            event_entity.end = event.timestamp
            event_entity.duration = (event.timestamp - event_entity.start).total_seconds()

            sess.add(event_entity)
            sess.commit()
            sess.refresh(event_entity)

            event_model = CameraEventBaseModel.model_validate(
                event_entity.to_dict(
                    include_relationships=True
                )
            )

            message = WebsocketMessageDetectionEnd(
                camera_id=event_model.camera.id,
                area_id=event_model.area.id,
                message=f'[{event_model.camera.name}] Motion detected end at {event_model.end}, duration: {event_model.duration}',
            )
            WebSockets.send_broadcast(message)

            CameraNotifier.active_events.remove(founded_event)

            # Publish motion end event
            event_bus.publish(EventType.MOTION_END, event=event_model)

            Logger.debug(
                f"🤚 [{event_model.camera.name} EvID#{event_model.id}] Конец движения в {event_model.area.name}. Время: {event_model.end}",
                LoggerType.CAMERAS,
                with_db=True,
                entity_code=LogEntityCode(
                    id=event_model.camera.id,
                    code=LogCode.CAMERA_MOTION_START
                ))

    @staticmethod
    def _on_recording_start(event: "ROIRecordEvent", stream: "CameraStream"):
        """Логирует факт начала записи с камеры.

        Args:
            event (ROIRecordEvent): Событие начала записи
        """
        Logger.debug(f"[{event.timestamp}] Начата запись с камеры {event.camera.name} в {event.timestamp}",
                     LoggerType.CAMERAS)

    @staticmethod
    def _on_recording_end(event: "ROIRecordEvent", stream: "CameraStream"):
        """Логирует факт окончания записи с камеры, включая продолжительность записи.

        Args:
            event (ROIRecordEvent): Событие окончания записи
        """
        with write_session() as sess:
            founded_record = CameraNotifier._find_active_recording(event.camera.id)
            if isinstance(founded_record, CameraRecordingModel):
                recording = sess.get(CameraRecordingEntity, founded_record.id)
                if isinstance(recording, CameraRecordingEntity):
                    recording.end = event.timestamp
                    recording.duration = (event.timestamp - recording.start).total_seconds()
                    recording.path = stream.output_file

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
                        f"[{recording.end}] Завершена запись с {event.camera.name}. Длительность: {recording.duration:.2f} сек",
                        LoggerType.CAMERAS)
                    stream.stop_write_video()

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
                Logger.err(error_msg, LoggerType.CAMERAS)

        thread = Thread(
            daemon=True,
            target=wrapped_target,
            name=f"CameraNotifierThread-{target.__name__}"  # Полезно для отладки
        )
        thread.start()
        Logger.debug(f"🐍 Запущен поток для обработки {target.__name__} (ID: {thread.native_id})", LoggerType.CAMERAS)
