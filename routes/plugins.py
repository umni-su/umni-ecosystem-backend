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

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import FileResponse
from typing import List, Dict, Any, Optional, TYPE_CHECKING, Annotated
from pydantic import BaseModel

from classes.auth.auth import Auth
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from config.dependencies import get_ecosystem
from models.plugin_model import PluginModel
from repositories.plugin_repository import PluginRepository
from responses.user import UserResponseOut

if TYPE_CHECKING:
    from services.plugins.plugins_service import PluginsService

plugins = APIRouter(prefix="/plugins", tags=["plugins"])


class PluginUpdateModel(BaseModel):
    display_name: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None
    options: Optional[Dict[str, Any]] = None


class PluginToggleModel(BaseModel):
    active: bool


@plugins.get("", response_model=List[PluginModel])
async def get_plugins(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    """Получение всех плагинов из БД"""
    try:
        _plugins = PluginRepository.get_plugins()
        return _plugins
    except Exception as e:
        Logger.err(f"Error getting plugins: {str(e)}", LoggerType.PLUGINS)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get plugins"
        )


@plugins.get("/available")
async def get_available_plugins(
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
):
    """Получение плагинов доступных для установки (еще не в БД)"""
    try:
        ecosystem = get_ecosystem()
        plugin_service: "PluginsService" = ecosystem.service_runner.get_service_by_name('plugins')
        if not plugin_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Plugin service not initialized"
            )

        # Получаем список плагинов из файловой системы
        available_plugins = []
        plugins_dir = plugin_service.plugins_dir / "custom"

        if plugins_dir.exists():
            for plugin_dir in plugins_dir.iterdir():
                if plugin_dir.is_dir():
                    plugin_name = plugin_dir.name

                    # Проверяем, есть ли уже в БД
                    existing_plugin = PluginRepository.get_plugin_by_name(plugin_name)
                    if not existing_plugin:
                        available_plugins.append({
                            "name": plugin_name,
                            "path": str(plugin_dir),
                            "can_install": True
                        })

        return available_plugins
    except Exception as e:
        Logger.err(f"Error getting available plugins: {str(e)}", LoggerType.PLUGINS)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get available plugins"
        )


@plugins.get("/{plugin_id}", response_model=PluginModel)
async def get_plugin(
        plugin_id: int,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)]
):
    """Получение одного плагина по ID"""
    try:
        plugin = PluginRepository.get_plugin(plugin_id)
        if not plugin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plugin not found"
            )
        return plugin
    except HTTPException:
        raise
    except Exception as e:
        Logger.err(f"Error getting plugin {plugin_id}: {str(e)}", LoggerType.PLUGINS)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get plugin"
        )


@plugins.post("/{plugin_name}/install", status_code=status.HTTP_201_CREATED)
async def install_plugin(plugin_name: str, force: bool = False):
    """Установка/переустановка плагина"""
    try:
        ecosystem = get_ecosystem()
        plugin_service: "PluginsService" = ecosystem.service_runner.get_service_by_name('plugins')
        if not plugin_service:
            raise HTTPException(status_code=503, detail="Plugin service not available")

        success = plugin_service.install_plugin(plugin_name, force=force)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to install plugin")

        action = "reinstalled" if force else "installed"
        return {"message": f"Plugin {plugin_name} {action} successfully"}

    except Exception as e:
        Logger.err(f"Error installing plugin {plugin_name}: {str(e)}", LoggerType.PLUGINS)
        raise HTTPException(status_code=500, detail="Failed to install plugin")


@plugins.post("/{plugin_name}/reinstall")
async def reinstall_plugin(plugin_name: str):
    """Переустановка плагина (синоним install с force=true)"""
    try:
        ecosystem = get_ecosystem()
        plugin_service: "PluginsService" = ecosystem.service_runner.get_service_by_name('plugins')
        if not plugin_service:
            raise HTTPException(status_code=503, detail="Plugin service not available")

        success = plugin_service.install_plugin(plugin_name, force=True)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to reinstall plugin")

        return {"message": f"Plugin {plugin_name} reinstalled successfully"}

    except Exception as e:
        Logger.err(f"Error reinstalling plugin {plugin_name}: {str(e)}", LoggerType.PLUGINS)
        raise HTTPException(status_code=500, detail="Failed to reinstall plugin")


@plugins.patch("/{plugin_id}", response_model=PluginModel)
async def update_plugin(
        plugin_id: int,
        update_data: PluginUpdateModel,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)]
):
    """Частичное обновление плагина"""
    try:
        ecosystem = get_ecosystem()
        plugin_service: "PluginsService" = ecosystem.service_runner.get_service_by_name('plugins')
        if not plugin_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Plugin service not initialized"
            )

        # Получаем текущий плагин
        current_plugin = PluginRepository.get_plugin(plugin_id)
        if not current_plugin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plugin not found"
            )

        # Обновляем в БД
        updated_plugin = PluginRepository.patch_plugin(plugin_id, update_data.dict(exclude_unset=True))
        if not updated_plugin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update plugin"
            )

        # Обновляем в сервисе плагинов
        success = plugin_service.refresh_plugin(current_plugin.name)
        if not success:
            Logger.warn(f"Plugin {current_plugin.name} updated in DB but failed to refresh in service",
                        LoggerType.PLUGINS)

        return updated_plugin

    except HTTPException:
        raise
    except Exception as e:
        Logger.err(f"Error updating plugin {plugin_id}: {str(e)}", LoggerType.PLUGINS)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update plugin"
        )


@plugins.post("/{plugin_id}/toggle")
async def toggle_plugin(
        plugin_id: int,
        toggle_data: PluginToggleModel,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)]
):
    """Включение/выключение плагина"""
    try:
        ecosystem = get_ecosystem()
        plugin_service: "PluginsService" = ecosystem.service_runner.get_service_by_name('plugins')
        if not plugin_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Plugin service not initialized"
            )

        # Получаем плагин
        plugin = PluginRepository.get_plugin(plugin_id)
        if not plugin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plugin not found"
            )

        # Обновляем активность в БД
        updated_plugin = PluginRepository.patch_plugin(plugin_id, {"active": toggle_data.active})
        if not updated_plugin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update plugin activity"
            )

        # Применяем изменения в сервисе
        success = plugin_service.toggle_plugin(plugin.name, toggle_data.active)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to {'start' if toggle_data.active else 'stop'} plugin"
            )

        action = "started" if toggle_data.active else "stopped"
        return {"message": f"Plugin {plugin.name} {action} successfully"}

    except HTTPException:
        raise
    except Exception as e:
        Logger.err(f"Error toggling plugin {plugin_id}: {str(e)}", LoggerType.PLUGINS)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to toggle plugin"
        )


@plugins.delete("/{plugin_id}")
async def delete_plugin(
        plugin_id: int,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)]
):
    """Удаление плагина"""
    try:
        ecosystem = get_ecosystem()
        plugin_service: "PluginsService" = ecosystem.service_runner.get_service_by_name('plugins')
        if not plugin_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Plugin service not initialized"
            )

        # Получаем плагин
        plugin = PluginRepository.get_plugin(plugin_id)
        if not plugin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plugin not found"
            )

        # Останавливаем плагин если запущен
        if plugin.active:
            plugin_service.toggle_plugin(plugin.name, False)

        # Удаляем из БД
        success = PluginRepository.delete_plugin(plugin_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete plugin from database"
            )

        # Удаляем из сервиса
        plugin_service.remove_plugin(plugin.name)

        return {"message": f"Plugin {plugin.name} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        Logger.err(f"Error deleting plugin {plugin_id}: {str(e)}", LoggerType.PLUGINS)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete plugin"
        )


@plugins.get("/{plugin_id}/status")
async def get_plugin_status(
        plugin_id: int,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)]
):
    """Получение статуса плагина из сервиса"""
    try:
        ecosystem = get_ecosystem()
        plugin_service: "PluginsService" = ecosystem.service_runner.get_service_by_name('plugins')
        if not plugin_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Plugin service not initialized"
            )

        plugin = PluginRepository.get_plugin(plugin_id)
        if not plugin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plugin not found"
            )

        status_info = plugin_service.get_plugin_status(plugin.name)
        if not status_info:
            status_info = {"status": "not_loaded"}

        return {
            "plugin_id": plugin_id,
            "plugin_name": plugin.name,
            **status_info
        }

    except HTTPException:
        raise
    except Exception as e:
        Logger.err(f"Error getting plugin status {plugin_id}: {str(e)}", LoggerType.PLUGINS)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get plugin status"
        )


@plugins.get("/{plugin_name}/logo")
async def get_plugin_logo(
        plugin_name: str,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)]
):
    """Получить логотип плагина"""
    try:
        ecosystem = get_ecosystem()
        plugin_service: "PluginsService" = ecosystem.service_runner.get_service_by_name('plugins')
        if not plugin_service:
            raise HTTPException(status_code=503, detail="Plugin service not available")

        # Путь к логотипу плагина
        plugin_dir = plugin_service.plugins_dir / "custom" / plugin_name
        logo_path = plugin_dir / "logo.png"
        default_logo_path = plugin_service.plugins_dir / "default.png"

        # Проверяем существование файлов
        if logo_path.exists():
            return FileResponse(
                str(logo_path),
                media_type="image/png",
                filename=f"{plugin_name}_logo.png",
                content_disposition_type='inline',
                headers={"Cache-Control": "public, max-age=3600"}
            )
        elif default_logo_path.exists():
            return FileResponse(
                str(default_logo_path),
                media_type="image/png",
                filename="default_logo.png",
                content_disposition_type='inline'
            )
        else:
            raise HTTPException(
                status_code=404,
                detail="Logo not found"
            )

    except HTTPException:
        raise
    except Exception as e:
        Logger.err(f"Error getting logo for {plugin_name}: {str(e)}", LoggerType.PLUGINS)
        raise HTTPException(
            status_code=500,
            detail="Failed to get plugin logo"
        )


@plugins.get("/{plugin_id}/schema")
async def get_plugin_schema(
        plugin_id: int,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)]
):
    """Получение статуса плагина из сервиса"""
    try:
        ecosystem = get_ecosystem()
        plugin_service: "PluginsService" = ecosystem.service_runner.get_service_by_name('plugins')
        if not plugin_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Plugin service not initialized"
            )

        plugin = PluginRepository.get_plugin(plugin_id)
        if not plugin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plugin not found"
            )

        return plugin_service.get_plugin_config_schema(plugin.name)

    except HTTPException:
        raise
    except Exception as e:
        Logger.err(f"Error getting plugin status {plugin_id}: {str(e)}", LoggerType.PLUGINS)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get plugin schema"
        )


@plugins.post("/{plugin_id}/schema")
def save_plugin_schema(
        plugin_id: int,
        model: Dict[str, Any],
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)]
):
    print(type(model), model.get('schema'))
    try:
        ecosystem = get_ecosystem()
        plugin_service: "PluginsService" = ecosystem.service_runner.get_service_by_name('plugins')
        if not plugin_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Plugin service not initialized"
            )

        plugin = PluginRepository.get_plugin(plugin_id)
        if not plugin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plugin not found"
            )

        return plugin_service.get_plugin_config_schema(plugin.name)
    except HTTPException:
        raise
    except Exception as e:
        Logger.err(f"Error getting plugin status {plugin_id}: {str(e)}", LoggerType.PLUGINS)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get plugin schema"
        )


@plugins.post("/{plugin_id}/execute")
def execute_plugin(
        plugin_id: int,
        user: Annotated[UserResponseOut, Depends(Auth.get_current_active_user)],
        data: Dict[str, Any] = None,

):
    """Выполнение плагина"""
    try:
        ecosystem = get_ecosystem()
        plugin_service: "PluginsService" = ecosystem.service_runner.get_service_by_name('plugins')
        if not plugin_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Plugin service not initialized"
            )

        plugin = PluginRepository.get_plugin(plugin_id)
        if not plugin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plugin not found"
            )

        if not plugin.active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Plugin is not active"
            )

        result = plugin_service.execute_plugin(plugin.name, data)
        return {"result": result}

    except HTTPException:
        raise
    except Exception as e:
        Logger.err(f"Error executing plugin {plugin_id}: {str(e)}", LoggerType.PLUGINS)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Plugin execution failed: {str(e)}"
        )
