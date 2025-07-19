import os.path
from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import select

from classes.logger import Logger
from classes.storages.camera_storage import CameraStorage
from entities.camera_area import CameraAreaEntity
from entities.camera_event import CameraEventEntity
from models.pagination_model import PageParams, PaginatedResponse
from repositories.area_repository import CameraAreaRepository
from repositories.base_repository import BaseRepository

if TYPE_CHECKING:
    from entities.camera import CameraEntity
    from services.cameras.classes.roi_tracker import ROIDetectionEvent


class CameraEventsRepository(BaseRepository):
    @classmethod
    def add_event(cls, model: "ROIDetectionEvent"):
        with cls.query() as sess:
            area = CameraAreaRepository.get_area(model.roi.id)
            if isinstance(area, CameraAreaEntity):
                try:
                    camera = area.camera
                    screenshot = CameraStorage.take_detection_screenshot(camera, model.frame)
                    event = CameraEventEntity()
                    event.camera = camera
                    event.area = area
                    event.start = datetime.now()
                    event.action = model.event
                    event.type = camera.record_mode
                    event.screenshot = os.path.join(screenshot.directory, screenshot.filename)

                    # Taking screenshot
                    # screenshot = stream.take_screenshot(
                    #     path=CameraStorage.screenshots_detections_path(camera),
                    #     prefix='motion_start',
                    #     frame=stream.tracker.draw_rois(
                    #         frame=stream.resized,
                    #         roi_id=event.roi.id
                    #     )
                    # )
                    #
                    # if screenshot.success:
                    #     event.screenshot = os.path.join(
                    #         screenshot.path,
                    #         screenshot.filename
                    #     )

                    sess.add(event)
                    sess.commit()
                    sess.refresh(event)

                    return event
                except Exception as e:
                    Logger.err(e)

    @classmethod
    def update_event_end(cls, event: CameraEventEntity):
        with cls.query() as sess:
            try:
                event.end = datetime.now()
                sess.add(event)
                sess.commit()
                sess.refresh(event)

                return event
            except Exception as e:
                Logger.err(e)

    @classmethod
    def get_events(cls, params: PageParams, camera: "CameraEntity"):
        with cls.query() as sess:
            # Получаем общее количество дочерних элементов
            total = sess.exec(
                select(CameraEventEntity).where(CameraEventEntity.camera.id == camera.id)
            ).count()

            # Вычисляем количество страниц
            pages = (total + params.size - 1)

            items = sess.exec(
                select(CameraEventEntity)
                .where(CameraEventEntity.camera.id == camera.id)
                .offset((params.page - 1) * params.size)
                .limit(params.size)
            ).all()

            return PaginatedResponse[CameraEventEntity](
                items=items,
                total=total,
                page=params.page,
                size=params.size,
                pages=pages
            )
