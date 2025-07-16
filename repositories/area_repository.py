from typing import TYPE_CHECKING

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
            for __area in areas:
                area = CameraAreaEntity()
                if __area.id is not None:
                    area = cls.get_area(__area.id)

                if area is not None:
                    if area.camera_id != camera.id:
                        area.camera = camera
                    area.name = __area.name
                    area.active = __area.active
                    area.color = __area.color
                    area.priority = __area.priority
                    area.points = __area.points

                    if __area.options is not None:
                        area.options = __area.options.model_dump()
                    else:
                        area.options = None

                    try:
                        session.add(area)
                        session.commit()
                        session.refresh(area)
                        session.refresh(camera)
                        return camera.areas
                    except Exception as e:
                        Logger.err(e)

    @classmethod
    def get_area(cls, area_id: int) -> CameraAreaEntity:
        with cls.query() as session:
            return session.exec(
                select(CameraAreaEntity)
                .where(CameraAreaEntity.id == area_id)
            ).first()
