from fastapi import HTTPException
from sqlmodel import select

from classes.logger import Logger
from entities.camera import CameraEntity
from entities.camera_area import CameraAreaEntity
from repositories.base_repository import BaseRepository

from models.camera_area_model import CameraAreaBaseModel


class CameraAreaRepository(BaseRepository):
    @classmethod
    def save_areas_data(cls, areas: list["CameraAreaBaseModel"], camera: CameraEntity):
        with cls.query() as session:
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

                session.commit()
                session.refresh(camera)
                return camera.areas

            except Exception as e:
                session.rollback()
                Logger.err(e)
                raise  # Или вернуть None/пустой список

    @classmethod
    def get_area(cls, area_id: int) -> CameraAreaEntity:
        with cls.query() as session:
            return session.exec(
                select(CameraAreaEntity)
                .where(CameraAreaEntity.id == area_id)
            ).first()

    @classmethod
    def delete_area(cls, area_id: int) -> list["CameraAreaEntity"]:
        with cls.query() as session:
            try:
                area = cls.get_area(area_id)
                if not area:
                    raise HTTPException(status_code=404, detail="Area not found")

                camera = area.camera
                session.delete(area)  # Events удалятся автоматически благодаря каскаду!
                session.commit()

                session.refresh(camera)  # Обновляем камеру, чтобы получить актуальный список areas
                return camera.areas

            except Exception as e:
                session.rollback()
                raise HTTPException(status_code=500, detail=str(e))
