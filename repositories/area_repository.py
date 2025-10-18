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

import typing
from typing import List

from fastapi import HTTPException
from sqlmodel import select, col

from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from database.session import write_session
from entities.camera_area import CameraAreaEntity
from repositories.base_repository import BaseRepository

from models.camera_area_model import CameraAreaBaseModel
from repositories.camera_repository import CameraRepository

if typing.TYPE_CHECKING:
    from models.camera_model import CameraModelWithRelations


class CameraAreaRepository(BaseRepository):
    entity_class = CameraAreaEntity
    model_class = CameraAreaBaseModel

    @classmethod
    def save_areas_data(cls, areas: list["CameraAreaBaseModel"], camera: "CameraModelWithRelations"):
        from services.cameras.classes.stream_registry import StreamRegistry

        try:
            result_areas = []
            # ВСЯ работа с БД в отдельном блоке
            with write_session() as session:
                existing_area_ids = [a.id for a in areas if a.id is not None]
                existing_areas = {}

                if existing_area_ids:
                    existing_areas = {a.id: a for a in session.exec(
                        select(CameraAreaEntity)
                        .where(
                            col(CameraAreaEntity.id).in_(existing_area_ids)
                        )
                    ).all()}

                for area_data in areas:
                    if area_data.id is not None and area_data.id in existing_areas:
                        area = existing_areas[area_data.id]
                    else:
                        area = CameraAreaEntity()

                    area.camera_id = camera.id
                    area.name = area_data.name
                    area.active = area_data.active
                    area.color = area_data.color
                    area.priority = area_data.priority.value
                    area.points = area_data.points
                    area.options = area_data.options.model_dump() if area_data.options else None

                    session.add(area)
                    session.flush()  # Важно: получаем ID без коммита

                    area_model = CameraAreaBaseModel.model_validate(
                        area.to_dict()
                    )
                    result_areas.append(area_model)

                session.commit()

            area_ids = [a.id for a in result_areas]

            # ✅ ВНЕ СЕССИИ обновляем трекер
            stream = StreamRegistry.find_by_camera(camera)
            if stream is not None:
                if stream and hasattr(stream, 'tracker'):
                    # Отложенное обновление без блокировки
                    import threading
                    threading.Thread(
                        target=stream.tracker.update_rois_by_ids,
                        args=(area_ids,),
                        daemon=True
                    ).start()

            return result_areas

        except Exception as e:
            Logger.err(f"Error saving areas: {e}", LoggerType.APP)
            raise

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
    def delete_area(cls, area_id: int) -> list[CameraAreaBaseModel] | None:
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
