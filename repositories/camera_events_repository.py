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

from datetime import datetime, timedelta
from math import ceil
from typing import TYPE_CHECKING

import numpy as np
import imutils
from sqlalchemy import func
from sqlmodel import select, col
from fastapi import HTTPException

from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from classes.storages.camera_storage import CameraStorage
from database.session import write_session
from entities.camera_event import CameraEventEntity
from entities.camera_recording import CameraRecordingEntity
from entities.enums.camera_record_type_enum import CameraRecordTypeEnum
from models.camera_event_model import CameraEventModel
from models.pagination_model import EventsPageParams, PaginatedResponse, EventsPageType, TimelineParams
from repositories.base_repository import BaseRepository
from services.cameras.classes.roi_tracker import ROIEventType

if TYPE_CHECKING:
    from models.camera_model import CameraModelWithRelations


class CameraEventsRepository(BaseRepository):
    """
    Добавляет новое событие для камеры с режимом периодических скриншотов или периодического видео
    """

    @classmethod
    def add_permanent_event(
            cls,
            camera: "CameraModelWithRelations",
            frame: np.ndarray,
            record_path: str | None = None
    ):
        with write_session() as session:
            try:
                has_record = False
                # Если у камеры режим периодического видео,
                # то нужно еще кроме события, создавать и запись в таблице camera_recordings
                action = ROIEventType.STATIC_SCREENSHOT
                if camera.record_mode == CameraRecordTypeEnum.VIDEO:
                    has_record = True
                    action = ROIEventType.STATIC_VIDEO
                resized = imutils.resize(frame, width=640)

                original_file = CameraStorage.take_screenshot(camera, frame).full_path
                resized_file = CameraStorage.take_screenshot(camera, resized).full_path

                event = CameraEventEntity()
                event.camera_id = camera.id
                event.area = None
                event.resized = resized_file
                event.original = original_file
                event.type = camera.record_mode.value
                event.action = action.value
                event.start = datetime.now()

                # Добавляем событие
                if has_record:
                    record = CameraRecordingEntity()
                    record.camera_id = camera.id
                    record.path = record_path
                    record.start = event.start
                    event.recording = record

                session.add(event)
                session.commit()
                session.refresh(event)

                return CameraEventModel.model_validate(
                    event.to_dict()
                )
            except Exception as e:
                Logger.err(f'[{camera.name}] Error adding permanent event: {e}', LoggerType.APP)

    @classmethod
    def close_permanent_event(cls, event: CameraEventModel):
        with write_session() as session:
            try:
                event = session.get(CameraEventEntity, event.id)
                event.end = datetime.now()
                event.duration = (event.end - event.start).total_seconds()

                if event.recording is not None:
                    event.recording.end = event.end
                    event.recording.duration = event.duration
                session.commit()
                return CameraEventModel.model_validate(
                    event.to_dict()
                )
            except Exception as e:
                event_id = event.id  # Сохраняем ID до закрытия сессии
                Logger.err(f'Error update end for permanent event #ID{event_id}: {e}', LoggerType.APP)

    @classmethod
    def update_event_end(cls, event: CameraEventEntity):
        with write_session() as sess:
            try:
                event.end = datetime.now()
                sess.add(event)
                sess.commit()
                sess.refresh(event)

                return event
            except Exception as e:
                Logger.err(f"update_event_end error - {e}", LoggerType.APP)

    @classmethod
    def get_event(cls, event_id: int, relations: bool = False):
        with (write_session() as sess):
            event = sess.get(CameraEventEntity, event_id)
            if not event:
                raise HTTPException(status_code=404)
            return CameraEventModel.model_validate(
                event.to_dict(
                    include_relationships=relations
                )
            )

    @classmethod
    def delete_event(cls, event_id: int):
        with write_session() as sess:
            try:
                event = sess.get(CameraEventEntity, event_id)
                recording = event.recording
                if recording is not None:
                    other_events_with_same_record = sess.exec(
                        select(CameraEventEntity).where(CameraEventEntity.camera_recording_id == recording.id)
                    ).all()
                    count = len(other_events_with_same_record)
                    if count == 1 and recording.id == other_events_with_same_record[0].id:
                        sess.delete(recording)
                sess.delete(event)
                return True
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=str(e)
                )

    @classmethod
    def get_old_events(cls, camera: "CameraModelWithRelations") -> list["CameraEventModel"]:
        with write_session() as sess:
            try:
                cutoff_time = datetime.now() - timedelta(minutes=camera.delete_after)
                res = sess.exec(
                    select(CameraEventEntity)
                    .where(
                        (CameraEventEntity.camera_id == camera.id) &
                        (CameraEventEntity.end < cutoff_time)
                    )
                ).all()
                return [
                    CameraEventModel.model_validate(
                        ev.to_dict(
                            include_relationsips=True
                        )
                    ) for ev in res
                ]
            except Exception as e:
                Logger.err(f"get_old_events error - {e}", LoggerType.APP)
                return []

    @classmethod
    def get_timeline(cls, params: TimelineParams, camera: "CameraModelWithRelations"):
        with write_session() as sess:
            try:
                query = (
                    select(CameraEventEntity)
                    .where(CameraEventEntity.camera_id == camera.id)
                    .where(CameraEventEntity.start >= params.start)
                    .where(CameraEventEntity.end <= params.end)
                )

                timeline_entries = sess.exec(query).all()
                return [
                    CameraEventModel.model_validate(
                        ev.to_dict()
                    )
                    for ev in timeline_entries
                ]
            except Exception as e:
                print(e)
                raise HTTPException(
                    status_code=500,
                    detail='Error get event timeline'
                )

    @classmethod
    def get_events(cls, params: EventsPageParams, camera: "CameraModelWithRelations"):
        with write_session() as sess:
            try:
                # Подготавливаем базовый запрос
                query = (
                    select(CameraEventEntity)
                    .where(CameraEventEntity.camera_id == camera.id)
                )

                count = select(func.count(col(CameraEventEntity.id))).where(CameraEventEntity.camera_id == camera.id)

                if params.event_id is not None:
                    event = cls.get_event(params.event_id)
                    if event is not None:
                        if params.direction == 'start':
                            query = query.where(CameraEventEntity.start >= event.start).where(
                                CameraEventEntity.id != event.id)
                            count = count.where(CameraEventEntity.start >= event.start).where(
                                CameraEventEntity.id != event.id)
                        elif params.direction == 'end':
                            query = query.where(CameraEventEntity.start <= event.start).where(
                                CameraEventEntity.id != event.id)
                            count = count.where(CameraEventEntity.start <= event.start).where(
                                CameraEventEntity.id != event.id)
                        else:
                            query = query.where(CameraEventEntity.start <= event.start)
                            count = count.where(CameraEventEntity.start <= event.start)

                if params.type == EventsPageType.STREAM:
                    _col = col(CameraEventEntity.type).in_(
                        [
                            CameraRecordTypeEnum.VIDEO,
                            CameraRecordTypeEnum.SCREENSHOTS
                        ]
                    )
                    query = query.where(_col)
                    count = count.where(_col)
                elif params.type == EventsPageType.EVENTS:
                    _col = col(CameraEventEntity.type).in_(
                        [
                            CameraRecordTypeEnum.DETECTION_VIDEO,
                            CameraRecordTypeEnum.DETECTION_SCREENSHOTS
                        ]
                    )
                    query = query.where(_col)
                    count = count.where(_col)
                # Получаем общее количество дочерних элементов
                total = sess.exec(count).first()

                # Вычисляем количество страниц
                pages = ceil(total / params.size) if params.size else 0

                items = sess.exec(
                    query.order_by(
                        col(CameraEventEntity.start).desc()
                    )
                    .offset((params.page - 1) * params.size)
                    .limit(params.size)
                ).all()

                model_items = [
                    CameraEventModel.model_validate(ev.to_dict())
                    for ev in items
                ]

                return PaginatedResponse[CameraEventModel](
                    items=model_items,
                    total=total,
                    page=params.page,
                    size=params.size,
                    pages=pages
                )
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)
