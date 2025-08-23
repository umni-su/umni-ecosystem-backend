from fastapi import HTTPException
from sqlmodel import select

from classes.logger import Logger
from database.database import write_session
from entities.camera import CameraEntity
from entities.camera_area import CameraAreaEntity
from repositories.base_repository import BaseRepository

from models.camera_area_model import CameraAreaBaseModel
from repositories.camera_repository import CameraRepository
from services.cameras.classes.stream_registry import StreamRegistry


class CameraAreaRepository(BaseRepository):
    @classmethod
    def save_areas_data(
            cls,
            areas: list["CameraAreaBaseModel"], camera: CameraEntity
    ):
        with write_session() as session:
            try:
                # Убедимся, что камера в сессии (без повторного добавления)
                camera = session.merge(camera)

                for __area in areas:
                    # Если есть ID, пытаемся получить существующую область
                    if __area.id is not None:
                        area = session.get(CameraAreaEntity, __area.id)  # Используем session.get вместо cls.get_area
                    else:
                        area = None

                    # Если область не найдена, создаем новую
                    if area is None:
                        area = CameraAreaEntity()
                    else:
                        # Если область найдена, убедимся, что она в текущей сессии
                        area = session.merge(area)

                    # Обновляем поля
                    area.camera = camera
                    area.name = __area.name
                    area.active = __area.active
                    area.color = __area.color
                    area.priority = __area.priority
                    area.points = __area.points
                    area.options = __area.options.model_dump() if __area.options is not None else None

                    session.add(area)

                    stream = StreamRegistry.find_by_camera(camera)
                    stream.tracker.update_all_rois(camera.areas)

                # session.refresh(camera)
                return camera.areas

            except Exception as e:
                Logger.err(e)

    @classmethod
    def get_camera_areas(cls, camera_id: int) -> list[CameraAreaBaseModel]:
        with write_session() as session:
            areas = session.exec(
                select(CameraAreaEntity)
                .where(CameraAreaEntity.camera_id == camera_id)
            ).all()
            return [CameraAreaBaseModel.model_validate(a.model_dump()) for a in areas]

    @classmethod
    def get_area(cls, area_id: int) -> CameraAreaEntity:
        with write_session() as session:
            return session.exec(
                select(CameraAreaEntity)
                .where(CameraAreaEntity.id == area_id)
            ).first()

    @classmethod
    def get_areas(cls) -> list[CameraAreaEntity]:
        with write_session() as session:
            return session.exec(
                select(CameraAreaEntity)
            ).all()

    @classmethod
    def delete_area(cls, area_id: int) -> list["CameraAreaEntity"]:
        with write_session() as session:
            try:
                area = cls.get_area(area_id)
                if not area:
                    raise HTTPException(status_code=404, detail="Area not found")

                session.delete(area)  # Events удалятся автоматически благодаря каскаду!

                # session.refresh(camera)  # Обновляем камеру, чтобы получить актуальный список areas
                camera = CameraRepository.get_camera(area.camera_id)
                return camera.areas

            except Exception as e:
                session.rollback()
                raise HTTPException(status_code=500, detail=str(e))
