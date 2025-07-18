from datetime import datetime

from classes.logger import Logger
from entities.camera_area import CameraAreaEntity
from entities.camera_event import CameraEventEntity
from repositories.area_repository import CameraAreaRepository
from repositories.base_repository import BaseRepository
from services.cameras.classes.roi_tracker import ROIDetectionEvent


class CameraEventsRepository(BaseRepository):
    @classmethod
    def add_event(cls, model: ROIDetectionEvent):
        with cls.query() as sess:
            area = CameraAreaRepository.get_area(model.roi.id)
            if isinstance(area, CameraAreaEntity):
                try:
                    camera = area.camera
                    event = CameraEventEntity()
                    event.camera = camera
                    event.area = area
                    event.start = datetime.now()
                    event.type = model.event

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
