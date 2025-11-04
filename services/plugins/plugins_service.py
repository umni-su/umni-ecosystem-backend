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

import importlib.util
import subprocess
import sys
import venv
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Type, Any
from warnings import deprecated

from sqlmodel import select

from classes.configuration.configuration import EcosystemDatabaseConfiguration
from classes.l10n.l10n import translator, plugin_translate
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from classes.thread.task_manager import TaskManager
from database.session import write_session
from entities.plugin_entity import PluginEntity
from models.plugin_model import PluginModel
from plugins.base_plugin import BasePlugin
from repositories.plugin_repository import PluginRepository
from services.base_service import BaseService


class PluginsService(BaseService):
    name = "plugins"

    def __init__(self, config: EcosystemDatabaseConfiguration):
        super().__init__(config)
        self._plugins: Dict[str, BasePlugin] = {}
        self._plugin_classes: Dict[str, Type[BasePlugin]] = {}
        self.task_manager: Optional[TaskManager] = None
        self.plugins_dir = Path("plugins")
        self._plugin_envs: Dict[str, str] = {}  # Пути к виртуальным окружениям плагинов

    def run(self):
        """Запуск сервиса плагинов"""
        Logger.info("Starting Plugin Service", LoggerType.PLUGINS)

        self.task_manager = TaskManager(max_workers=5)
        self._load_all_plugins()
        self._start_active_plugins()

        Logger.info("Plugin Service started", LoggerType.PLUGINS)

    def stop(self):
        """Остановка сервиса плагинов"""
        Logger.info("Stopping Plugin Service", LoggerType.PLUGINS)

        for plugin_name, plugin_instance in list(self._plugins.items()):
            self._stop_single_plugin(plugin_name)

        if self.task_manager:
            self.task_manager.stop()

        Logger.info("Plugin Service stopped", LoggerType.PLUGINS)

    def restart(self):
        """Перезапуск сервиса"""
        self.stop()
        self.run()

    def _load_all_plugins(self):
        """Загрузка всех плагинов из папки custom"""
        custom_plugins_dir = self.plugins_dir / "custom"

        if not custom_plugins_dir.exists():
            Logger.warn("Custom plugins directory not found", LoggerType.PLUGINS)
            return

        self._load_plugins_from_directory(custom_plugins_dir)
        self._sync_with_database()

    def _load_plugins_from_directory(self, directory: Path):
        """Загрузка плагинов из указанной директории"""
        for plugin_dir in directory.iterdir():
            if plugin_dir.is_dir():
                self.load_single_plugin(plugin_dir)

    def load_single_plugin(self, plugin_dir: Path):
        """Загрузка одного плагина с изолированным venv"""
        plugin_name = plugin_dir.name
        plugin_file = plugin_dir / f"{plugin_name}_plugin.py"

        if not plugin_file.exists():
            Logger.warn(f"Plugin file not found: {plugin_file}", LoggerType.PLUGINS)
            return

        try:
            # 1. Создаем/настраиваем виртуальное окружение для плагина
            env_path = self._setup_plugin_environment(plugin_dir, plugin_name)
            if not env_path:
                Logger.err(f"Failed to setup environment for {plugin_name}", LoggerType.PLUGINS)
                return

            # 2. Добавляем site-packages из venv в sys.path для импорта
            env_site_packages = self._get_env_site_packages(env_path)
            if env_site_packages not in sys.path:
                sys.path.insert(0, env_site_packages)

            # 3. Динамическая загрузка модуля (теперь зависимости будут из venv)
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            plugin_split = plugin_name.split("_")
            new_plugin_split = [s.capitalize() for s in plugin_split]

            # 4. Поиск класса плагина
            plugin_class_name = f"{''.join(new_plugin_split)}Plugin"
            plugin_class = getattr(module, plugin_class_name, None)

            # 5. Загружаем переводы плагина если есть
            plugin_locale_dir = plugin_dir / "l10n"
            if plugin_locale_dir.exists():
                translator.add_plugin_translations(plugin_name, plugin_locale_dir)

            if plugin_class and issubclass(plugin_class, BasePlugin):
                plugin_class.plugin_name = plugin_name

                # Загружаем конфиг если есть
                config_file = plugin_dir / f"{plugin_name}_config.json"
                if config_file.exists():
                    plugin_class.load_config(plugin_name)

                self._plugin_classes[plugin_name] = plugin_class
                self._plugin_envs[plugin_name] = env_path
                Logger.info(f"Plugin {plugin_name} loaded with isolated environment", LoggerType.PLUGINS)
            else:
                Logger.err(f"Plugin class {plugin_class_name} not found for {plugin_name}", LoggerType.PLUGINS)

        except ImportError as e:
            Logger.err(f"Plugin {plugin_name} import error - dependencies issue: {str(e)}", LoggerType.PLUGINS)
        except Exception as e:
            Logger.err(f"Error loading plugin {plugin_name}: {str(e)}", LoggerType.PLUGINS)

    def _setup_plugin_environment(self, plugin_dir: Path, plugin_name: str) -> Optional[str]:
        """Создание и настройка виртуального окружения для плагина"""
        env_path = plugin_dir / ".venv"
        requirements_file = plugin_dir / "requirements.txt"

        try:
            # Создаем виртуальное окружение если его нет
            if not env_path.exists():
                Logger.info(f"Creating virtual environment for {plugin_name}", LoggerType.PLUGINS)
                venv.create(env_path, with_pip=True)

            # Получаем пути к pip и python
            pip_path = self._get_env_pip_path(env_path)
            python_path = self._get_env_python_path(env_path)

            if not pip_path or not python_path:
                Logger.err(f"Failed to find pip/python in venv for {plugin_name}", LoggerType.PLUGINS)
                return None

            # ВСЕГДА устанавливаем/обновляем зависимости если есть requirements.txt
            if requirements_file.exists():
                Logger.info(f"Installing dependencies for {plugin_name}", LoggerType.PLUGINS)

                result = subprocess.run([
                    python_path, "-m", "pip", "install", "-r", str(requirements_file)
                ], capture_output=True, text=True, timeout=300)

                if result.returncode != 0:
                    Logger.err(f"Failed to install dependencies for {plugin_name}: {result.stderr}", LoggerType.PLUGINS)
                    return None
                else:
                    Logger.info(f"Dependencies installed for {plugin_name}", LoggerType.PLUGINS)

            return str(env_path)

        except subprocess.TimeoutExpired:
            Logger.err(f"Timeout installing dependencies for {plugin_name}", LoggerType.PLUGINS)
            return None
        except Exception as e:
            Logger.err(f"Error setting up environment for {plugin_name}: {str(e)}", LoggerType.PLUGINS)
            return None

    def _get_env_pip_path(self, env_path: Path) -> Optional[str]:
        """Получение пути к pip в виртуальном окружении"""
        # Для Windows
        if sys.platform == "win32":
            pip_path = env_path / "Scripts" / "pip.exe"
            if pip_path.exists():
                return str(pip_path)
        # Для Linux/Mac
        else:
            pip_path = env_path / "bin" / "pip"
            if pip_path.exists():
                return str(pip_path)

        return None

    def _get_env_python_path(self, env_path: Path) -> Optional[str]:
        """Получение пути к python в виртуальном окружении"""
        # Для Windows
        if sys.platform == "win32":
            python_path = env_path / "Scripts" / "python.exe"
            if python_path.exists():
                return str(python_path)
        # Для Linux/Mac
        else:
            python_path = env_path / "bin" / "python"
            if python_path.exists():
                return str(python_path)

        return None

    def _get_env_site_packages(self, env_path: str) -> str:
        """Получение пути к site-packages виртуального окружения"""
        env_path_obj = Path(env_path)

        # Для Windows
        if sys.platform == "win32":
            site_packages = env_path_obj / "Lib" / "site-packages"
        # Для Linux/Mac
        else:
            python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
            site_packages = env_path_obj / "lib" / python_version / "site-packages"

        return str(site_packages)

    def _sync_with_database(self):
        """Синхронизация плагинов с базой данных"""
        with write_session() as session:
            db_plugins = session.exec(select(PluginEntity)).all()
            db_plugin_names = {p.name for p in db_plugins}

            # Добавление новых плагинов в базу
            for plugin_name in self._plugin_classes.keys():
                if plugin_name not in db_plugin_names:
                    plugin_class = self._plugin_classes[plugin_name]
                    new_plugin = PluginEntity(
                        name=plugin_name,
                        display_name=plugin_class.plugin_config_model.display_name,
                        description=plugin_class.plugin_config_model.description,
                        version=plugin_class.plugin_config_model.version,
                        url=plugin_class.plugin_config_model.url,
                        author=plugin_class.plugin_config_model.author,
                        active=False,
                        status="stopped"
                    )
                    session.add(new_plugin)
                    Logger.info(f"Created database entry for plugin {plugin_name}", LoggerType.PLUGINS)

            # Удаление плагинов, которых нет в файловой системе
            for db_plugin in db_plugins:
                if db_plugin.name not in self._plugin_classes:
                    Logger.info(f"Removing orphaned plugin from database: {db_plugin.name}", LoggerType.PLUGINS)
                    session.delete(db_plugin)

            session.commit()

    def _start_active_plugins(self):
        """Запуск всех активных плагинов"""
        with write_session() as session:
            active_plugins = session.exec(
                select(PluginEntity).where(PluginEntity.active == True)
            ).all()

            for plugin_entity in active_plugins:
                self._start_single_plugin(plugin_entity.name)

    def _start_single_plugin(self, plugin_name: str) -> bool:
        """Запуск одного плагина"""
        try:
            if plugin_name not in self._plugin_classes:
                Logger.err(f"Plugin {plugin_name} not found", LoggerType.PLUGINS)
                return False

            # print(self._plugins[plugin_name].daemon)

            with write_session() as session:
                plugin_entity = session.exec(
                    select(PluginEntity).where(PluginEntity.name == plugin_name)
                ).first()

                if not plugin_entity:
                    Logger.err(f"Plugin {plugin_name} not found in database", LoggerType.PLUGINS)
                    return False

                # Создание экземпляра плагина с актуальными данными из БД
                plugin_model = PluginModel.model_validate(plugin_entity)
                plugin_instance = self._plugin_classes[plugin_name](plugin_model)

                plugin_instance.on_start()
                self._plugins[plugin_name] = plugin_instance

                # Обновление статуса
                plugin_entity.status = "running"
                plugin_entity.error_message = None
                session.add(plugin_entity)
                session.commit()

                Logger.info(f"Plugin {plugin_name} started successfully", LoggerType.PLUGINS)
                return True

        except Exception as e:
            error_msg = str(e)
            Logger.err(f"Error starting plugin {plugin_name}: {error_msg}", LoggerType.PLUGINS)
            self._mark_plugin_error(plugin_name, error_msg)
            return False

    def _stop_single_plugin(self, plugin_name: str) -> bool:
        """Остановка одного плагина"""
        try:
            if plugin_name not in self._plugins:
                return True

            plugin_instance = self._plugins[plugin_name]
            plugin_instance.on_stop()
            del self._plugins[plugin_name]

            with write_session() as session:
                plugin_entity = session.exec(
                    select(PluginEntity).where(PluginEntity.name == plugin_name)
                ).first()
                if plugin_entity:
                    plugin_entity.status = "stopped"
                    session.add(plugin_entity)
                    session.commit()

            Logger.info(f"Plugin {plugin_name} stopped successfully", LoggerType.PLUGINS)
            return True

        except Exception as e:
            Logger.err(f"Error stopping plugin {plugin_name}: {str(e)}", LoggerType.PLUGINS)
            return False

    def _mark_plugin_error(self, plugin_name: str, error_message: str):
        """Пометить плагин как ошибочный в базе данных"""
        with write_session() as session:
            plugin_entity = session.exec(
                select(PluginEntity).where(PluginEntity.name == plugin_name)
            ).first()
            if plugin_entity:
                plugin_entity.status = "error"
                plugin_entity.error_message = error_message
                session.add(plugin_entity)
                session.commit()

    # ОСНОВНЫЕ ПУБЛИЧНЫЕ МЕТОДЫ ДЛЯ РАБОТЫ С ПЛАГИНАМИ

    def get_plugin_status(self, plugin_name: str) -> Optional[Dict]:
        """Получение статуса плагина"""
        if plugin_name in self._plugins:
            plugin = self._plugins[plugin_name]
            return {
                "name": plugin.name,
                "is_running": plugin.is_running,
                "status": "running"
            }

        # Если плагин не запущен, проверяем его наличие
        if plugin_name in self._plugin_classes:
            return {
                "name": plugin_name,
                "is_running": False,
                "status": "stopped"
            }

        return None

    def get_plugins_list(self) -> List[Dict[str, Any]]:
        """Получить список всех загруженных плагинов с их статусами"""
        plugins_list = []

        for plugin_name, plugin_class in self._plugin_classes.items():
            plugin_info = {
                "name": plugin_name,
                "class_name": plugin_class.__name__,
                "loaded": True,
                "has_instance": plugin_name in self._plugins,
                "has_environment": plugin_name in self._plugin_envs
            }

            # Добавляем статус выполнения
            if plugin_name in self._plugins:
                plugin_instance = self._plugins[plugin_name]
                plugin_info.update({
                    "is_running": plugin_instance.is_running,
                    "status": "running" if plugin_instance.is_running else "stopped"
                })
            else:
                plugin_info.update({
                    "is_running": False,
                    "status": "not_started"
                })

            # Добавляем информацию из БД
            with write_session() as session:
                db_plugin = session.exec(
                    select(PluginEntity).where(PluginEntity.name == plugin_name)
                ).first()
                if db_plugin:
                    plugin_info.update({
                        "display_name": db_plugin.display_name,
                        "version": db_plugin.version,
                        "active": db_plugin.active,
                        "db_status": db_plugin.status,
                        "description": db_plugin.description,
                        "config": db_plugin.config
                    })

            plugins_list.append(plugin_info)

        return plugins_list

    def remove_plugin(self, plugin_name: str) -> bool:
        """Удаление плагина из сервиса (без удаления из БД)"""
        try:
            # Останавливаем если запущен
            if plugin_name in self._plugins:
                self._stop_single_plugin(plugin_name)

            # Удаляем из кэша
            if plugin_name in self._plugin_classes:
                del self._plugin_classes[plugin_name]
            if plugin_name in self._plugin_envs:
                del self._plugin_envs[plugin_name]

            Logger.info(f"Plugin {plugin_name} removed from service", LoggerType.PLUGINS)
            return True

        except Exception as e:
            Logger.err(f"Error removing plugin {plugin_name}: {str(e)}", LoggerType.PLUGINS)
            return False

    def refresh_plugin(self, plugin_name: str) -> bool:
        """Обновить плагин после изменений в БД"""
        try:
            # Останавливаем если запущен
            was_running = plugin_name in self._plugins
            if was_running:
                self._stop_single_plugin(plugin_name)

            # Перезагружаем плагин с новыми настройками
            plugin_dir = self.plugins_dir / "custom" / plugin_name
            if plugin_dir.exists():
                # Перезагружаем класс плагина
                if plugin_name in self._plugin_classes:
                    del self._plugin_classes[plugin_name]
                if plugin_name in self._plugin_envs:
                    del self._plugin_envs[plugin_name]

                self.load_single_plugin(plugin_dir)

                # Запускаем если был активен
                if was_running and plugin_name in self._plugin_classes:
                    self._start_single_plugin(plugin_name)

                Logger.info(f"Plugin {plugin_name} refreshed successfully", LoggerType.PLUGINS)
                return True

            return False

        except Exception as e:
            Logger.err(f"Error refreshing plugin {plugin_name}: {str(e)}", LoggerType.PLUGINS)
            return False

    def update_plugin_config(self, plugin_name: str, new_config: Dict[str, Any]) -> bool:
        """Обновление конфигурации плагина в БД и перезапуск если нужно"""
        try:
            with write_session() as session:
                plugin_entity = session.exec(
                    select(PluginEntity).where(PluginEntity.name == plugin_name)
                ).first()

                if not plugin_entity:
                    return False

                # Валидация конфигурации
                if plugin_name in self._plugin_classes:
                    plugin_class = self._plugin_classes[plugin_name]
                    temp_instance = plugin_class(PluginModel.from_orm(plugin_entity))
                    if not temp_instance.validate_config(new_config):
                        return False

                # Сохраняем новую конфигурацию
                plugin_entity.config = new_config
                session.add(plugin_entity)
                session.commit()

            # Обновляем конфигурацию запущенного плагина
            if plugin_name in self._plugins:
                self._plugins[plugin_name].on_config_update(new_config)

            Logger.info(f"Plugin {plugin_name} config updated", LoggerType.PLUGINS)
            return self.refresh_plugin(plugin_name)

        except Exception as e:
            Logger.err(f"Error updating plugin config {plugin_name}: {str(e)}", LoggerType.PLUGINS)
            return False

    def toggle_plugin(self, plugin_name: str, active: bool) -> bool:
        """Включение/выключение плагина"""
        try:
            with write_session() as session:
                plugin_entity = session.exec(
                    select(PluginEntity).where(PluginEntity.name == plugin_name)
                ).first()

                if not plugin_entity:
                    return False

                plugin_entity.active = active
                session.add(plugin_entity)
                session.commit()

                plugin_status = self.get_plugin_status(plugin_name)
                if plugin_status is not None:
                    if plugin_status['is_running'] and not active:
                        return self._stop_single_plugin(plugin_name)
                    elif not plugin_status['is_running'] and active:
                        return self._start_single_plugin(plugin_name)

                return False


        except Exception as e:
            Logger.err(f"Error toggling plugin {plugin_name}: {str(e)}", LoggerType.PLUGINS)
            return False

    @deprecated('This method will be deprecated')
    def execute_plugin(self, plugin_name: str, data: Dict[str, Any] = None) -> Any:
        """Выполнение плагина"""
        if plugin_name not in self._plugins:
            raise ValueError(f"Plugin {plugin_name} is not running")

        plugin_instance = self._plugins[plugin_name]

        if self.task_manager:
            return self.task_manager.submit(
                plugin_instance.execute,
                data=data
            )
        else:
            return plugin_instance.execute(data)

    def get_plugin_details(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """Получить детальную информацию о плагине"""
        plugins_list = self.get_plugins_list()
        for plugin in plugins_list:
            if plugin["name"] == plugin_name:
                return plugin
        return None

    def get_plugin_config_schema(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """Получить детальную информацию о плагине"""
        plugin = self._plugin_classes[plugin_name]
        if plugin:
            return plugin.config.get_ui_schema()
        return None

    def reload_all_plugins(self) -> Dict[str, bool]:
        """Перезагрузить все плагины (например, после массового обновления БД)"""
        results = {}

        # Останавливаем все плагины
        for plugin_name in list(self._plugins.keys()):
            self._stop_single_plugin(plugin_name)

        # Перезагружаем каждый плагин
        for plugin_name in self._plugin_classes.keys():
            results[plugin_name] = self.refresh_plugin(plugin_name)

        return results

    # ОБНОВЛЕННЫЕ МЕТОДЫ УСТАНОВКИ/УДАЛЕНИЯ

    def install_plugin(self, plugin_name: str, force: bool = False) -> bool:
        """Установка/переустановка плагина"""
        try:
            plugin_dir = self.plugins_dir / "custom" / plugin_name
            if not plugin_dir.exists():
                Logger.err(f"Plugin directory not found: {plugin_dir}", LoggerType.PLUGINS)
                return False

            # 1. Останавливаем плагин если запущен
            if plugin_name in self._plugins:
                self._stop_single_plugin(plugin_name)

            # 2. При принудительной переустановке удаляем venv
            env_path = plugin_dir / ".venv"
            if force and env_path.exists():
                shutil.rmtree(env_path)
                Logger.info(f"Force removed environment for {plugin_name}", LoggerType.PLUGINS)

            # 3. Удаляем из кэша
            if plugin_name in self._plugin_classes:
                del self._plugin_classes[plugin_name]
            if plugin_name in self._plugin_envs:
                del self._plugin_envs[plugin_name]

            # 4. Загружаем плагин заново (создаст/обновит venv)
            self.load_single_plugin(plugin_dir)

            # 5. Обновляем БД - ставим active=False
            dir_plugin = self._plugin_classes[plugin_name]
            current_plugin = PluginRepository.get_plugin_by_name(plugin_name)

            if current_plugin:
                current_plugin.active = False
                current_plugin.description = dir_plugin.plugin_config_model.description,
                current_plugin.name = plugin_name,
                current_plugin.author = dir_plugin.plugin_config_model.author,
                current_plugin.url = dir_plugin.plugin_config_model.url,
                current_plugin.version = dir_plugin.plugin_config_model.version,
                current_plugin.status = "stopped"
                PluginRepository.update_plugin(current_plugin.id, current_plugin)
            else:
                # Создаем новую запись если плагина нет в БД
                new_plugin = PluginModel(
                    name=plugin_name,
                    display_name=dir_plugin.plugin_config_model.display_name,
                    version=dir_plugin.plugin_config_model.version,
                    url=dir_plugin.plugin_config_model.url,
                    author=dir_plugin.plugin_config_model.author,
                    active=False,
                    description=dir_plugin.plugin_config_model.description,
                    status="stopped"
                )
                PluginRepository.create_plugin(new_plugin)

            Logger.info(f"Plugin {plugin_name} installed successfully (force={force})", LoggerType.PLUGINS)
            return True

        except Exception as e:
            Logger.err(f"Error installing plugin {plugin_name}: {str(e)}", LoggerType.PLUGINS)
            return False

    def uninstall_plugin(self, plugin_name: str) -> bool:
        """Удаление плагина (деактивация в БД и очистка окружения)"""
        try:
            # 1. Останавливаем плагин если запущен
            if plugin_name in self._plugins:
                self._stop_single_plugin(plugin_name)

            # 2. Устанавливаем active=False в БД
            with write_session() as session:
                plugin_entity = session.exec(
                    select(PluginEntity).where(PluginEntity.name == plugin_name)
                ).first()

                if plugin_entity:
                    plugin_entity.active = False
                    plugin_entity.status = "uninstalled"
                    session.add(plugin_entity)
                    session.commit()

            # 3. Удаляем из кэша сервиса
            if plugin_name in self._plugin_classes:
                del self._plugin_classes[plugin_name]
            if plugin_name in self._plugin_envs:
                del self._plugin_envs[plugin_name]

            # 4. Удаляем виртуальное окружение
            plugin_dir = self.plugins_dir / "custom" / plugin_name
            env_path = plugin_dir / ".venv"
            if env_path.exists():
                shutil.rmtree(env_path)
                Logger.info(f"Removed environment for {plugin_name}", LoggerType.PLUGINS)

            Logger.info(f"Plugin {plugin_name} uninstalled successfully", LoggerType.PLUGINS)
            return True

        except Exception as e:
            Logger.err(f"Error uninstalling plugin {plugin_name}: {str(e)}", LoggerType.PLUGINS)
            return False

    def download_install_plugin(self, url: str) -> bool:
        """Заглушка для будущей реализации установки плагина по URL"""
        Logger.info(f"Download install from URL would be implemented: {url}", LoggerType.PLUGINS)
        return False
