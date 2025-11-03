# Copyright (C) 2025 Mikhail Sazanov
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# repositories/plugin_repository.py
from sqlmodel import select, col
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from database.session import write_session
from entities.plugin_entity import PluginEntity
from models.plugin_model import PluginModel
from repositories.base_repository import BaseRepository


class PluginRepository(BaseRepository):
    entity_class = PluginEntity
    model_class = PluginModel

    @classmethod
    def get_plugins(cls):
        with write_session() as sess:
            try:
                plugins_orm = sess.exec(
                    select(PluginEntity).order_by(
                        col(PluginEntity.id).desc()
                    )
                ).all()
                return [
                    PluginModel.model_validate(
                        p.to_dict()
                    )
                    for p in plugins_orm
                ]
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)
                return []

    @classmethod
    def get_plugin(cls, plugin_id: int) -> PluginModel | None:
        with write_session() as sess:
            try:
                plugin_orm = sess.get(PluginEntity, plugin_id)
                if not plugin_orm:
                    return None
                return PluginModel.model_validate(
                    plugin_orm.to_dict()
                )
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)
                return None

    @classmethod
    def get_plugin_by_name(cls, plugin_name: str) -> PluginModel | None:
        with write_session() as sess:
            try:
                plugin_orm = sess.exec(
                    select(PluginEntity).where(PluginEntity.name == plugin_name)
                ).first()
                if not plugin_orm:
                    return None
                return PluginModel.model_validate(
                    plugin_orm.to_dict()
                )
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)
                return None

    @classmethod
    def create_plugin(cls, model: PluginModel) -> PluginModel | None:
        with write_session() as sess:
            try:
                plugin_entity = PluginEntity()
                plugin_entity.name = model.name
                plugin_entity.display_name = model.display_name
                plugin_entity.version = model.version
                plugin_entity.description = model.description
                plugin_entity.active = model.active
                plugin_entity.config = model.config
                plugin_entity.author = model.author
                plugin_entity.url = model.url
                plugin_entity.status = model.status
                plugin_entity.error_message = model.error_message

                sess.add(plugin_entity)
                sess.commit()
                sess.refresh(plugin_entity)

                return PluginModel.model_validate(
                    plugin_entity.to_dict()
                )
            except Exception as e:
                Logger.err(str(e), LoggerType.PLUGINS)
                return None

    @classmethod
    def update_plugin(cls, plugin_id: int, model: PluginModel) -> PluginModel | None:
        with write_session() as sess:
            try:
                plugin_entity = sess.get(PluginEntity, plugin_id)
                if not plugin_entity:
                    return None

                plugin_entity.name = model.name
                plugin_entity.display_name = model.display_name
                plugin_entity.version = model.version
                plugin_entity.description = model.description
                plugin_entity.active = model.active
                plugin_entity.author = model.author
                plugin_entity.url = model.url
                plugin_entity.config = model.config
                plugin_entity.status = model.status
                plugin_entity.error_message = model.error_message

                sess.add(plugin_entity)
                sess.commit()
                sess.refresh(plugin_entity)

                return PluginModel.model_validate(
                    plugin_entity.to_dict()
                )
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)
                return None

    @classmethod
    def patch_plugin(cls, plugin_id: int, update_data: dict) -> PluginModel | None:
        """Частичное обновление плагина"""
        with write_session() as sess:
            try:
                plugin_entity = sess.get(PluginEntity, plugin_id)
                if not plugin_entity:
                    return None

                # Обновляем только переданные поля
                for field, value in update_data.items():
                    if hasattr(plugin_entity, field):
                        setattr(plugin_entity, field, value)

                sess.add(plugin_entity)
                sess.commit()
                sess.refresh(plugin_entity)

                return PluginModel.model_validate(
                    plugin_entity.to_dict()
                )
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)
                return None

    @classmethod
    def delete_plugin(cls, plugin_id: int) -> bool:
        with write_session() as sess:
            try:
                plugin_entity = sess.get(PluginEntity, plugin_id)
                if not plugin_entity:
                    return False

                sess.delete(plugin_entity)
                sess.commit()
                return True
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)
                return False

    @classmethod
    def get_active_plugins(cls):
        with write_session() as sess:
            try:
                plugins_orm = sess.exec(
                    select(PluginEntity).where(
                        PluginEntity.active == True
                    )
                ).all()
                return [
                    PluginModel.model_validate(
                        p.to_dict()
                    )
                    for p in plugins_orm
                ]
            except Exception as e:
                Logger.err(str(e), LoggerType.APP)
                return []

    @classmethod
    def get_available_plugins_for_install(cls) -> list[dict]:
        """Получение списка плагинов доступных для установки (еще нет в БД)"""
        # Этот метод будет работать с файловой системой
        # Пока заглушка - реальная реализация будет сканировать папки
        return []
