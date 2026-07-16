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
import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, Type, List

from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from models.device_scan_model import DeviceScanModel
from repositories.device_repository import DeviceRepository
from classes.devices.device_manager import DeviceManager, device_manager
from classes.l10n.l10n import translator, plugin_translate
from classes.thread.daemon import Daemon
from classes.ui.ui_form_generator import UIEnhancedModel
from models.plugin_model import PluginModel, PluginConfigModel
from repositories.plugin_repository import PluginRepository


class BasePluginConfig(UIEnhancedModel):
    """Базовый класс для конфигурации плагина"""

    pass


class BasePlugin(ABC):
    """Абстрактный базовый класс для всех плагинов"""

    # Класс конфигурации для этого плагина (должен быть переопределён в дочерних классах)
    config_class: Type[BasePluginConfig] = BasePluginConfig

    plugin_config_model: PluginConfigModel = PluginConfigModel()
    plugin_dir = "plugins"
    daemon: Daemon | None = None
    is_core: bool = False
    _is_running: bool = False
    plugin_name = None
    manager: DeviceManager
    repository: DeviceRepository
    db_plugin: PluginModel
    db_id: int

    def __init__(self, plugin_model: PluginModel):
        try:
            self.plugin_model = plugin_model
            self._is_running = False
            self._config_instance: Optional[BasePluginConfig] = None
            self.manager = device_manager
            self.repository: DeviceRepository = DeviceRepository()
            self.db_plugin = PluginRepository.get_plugin_by_name(self.name)
            self.db_id = self.db_plugin.id
        except Exception as e:
            Logger.err(f'Could not start plugin {str(e)}', LoggerType.PLUGINS)
            self.on_stop()

        # Автоматическая валидация конфигурации при создании
        self._load_config()

    def _load_config(self):
        """Загружает и валидирует конфигурацию"""
        if self.plugin_model and self.plugin_model.config:
            try:
                self._config_instance = self.config_class.model_validate(self.plugin_model.config)
            except Exception as e:
                print(f"Config validation error for {self.name}: {e}")
                self._config_instance = self.config_class()  # пустой конфиг
        else:
            self._config_instance = self.config_class()  # пустой конфиг

    @property
    def config(self) -> BasePluginConfig:
        """
        Доступ к валидированной конфигурации.
        Всегда возвращает экземпляр (пустой, если нет конфига)
        """
        if self._config_instance is None:
            self._config_instance = self.config_class()
        return self._config_instance

    def get_ui_schema(self) -> Dict[str, Any]:
        """
        Возвращает схему для UI.
        Этот метод вызывается извне для получения описания полей конфигурации.
        """
        # Создаём временный экземпляр конфига для получения схемы
        # Важно: не используем self.config, так как там могут быть реальные значения
        return self.config_class().get_ui_schema()

    @classmethod
    def translate(cls, message: str, **kwargs) -> str:
        """Статический метод для переводов в конфигах"""
        if cls.plugin_name:
            return plugin_translate(
                plugin_name=cls.plugin_name,
                message=message,
                **kwargs
            )
        if kwargs:
            try:
                return message.format(**kwargs)
            except (KeyError, ValueError):
                return message
        return message

    def _(self, message: str, **kwargs) -> str:
        """Функция перевода для плагина"""
        return self.translate(message, **kwargs)

    def get_current_language(self) -> str:
        """Получить текущий язык"""
        return translator.get_default_lang()

    @classmethod
    def load_config(cls, config_file: Path):
        """Загрузка мета-конфигурации из файла"""
        if os.path.exists(os.path.abspath(config_file)):
            with open(config_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                cls.plugin_config_model = PluginConfigModel.model_validate(json_data)
        else:
            print('config file not found', config_file)

    @property
    def name(self) -> str:
        return self.plugin_model.name

    @property
    def version(self) -> str:
        return self.plugin_model.version

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def directory(self) -> str:
        return "core" if self.is_core else "custom"

    @abstractmethod
    def execute(self, data: Dict[str, Any] = None) -> Any:
        """Основной метод выполнения плагина"""
        pass

    def scan_devices(self) -> List[DeviceScanModel]:
        """
        Сканирование устройств.
        Вызывается из API эндпойнта /plugins/{id}/scan

        Returns:
            List[DeviceScanModel]: список обнаруженных устройств
        """
        return []

    def on_start(self, data: Dict[str, Any] = None):
        """Вызывается при запуске плагина"""
        started = self._is_running
        self._is_running = True
        if not started:
            from threading import Thread
            thread = Thread(
                target=self.execute,
                args=(data,),
                daemon=True
            )
            thread.start()

    def on_stop(self):
        """Вызывается при остановке плагина"""
        self._is_running = False

    def on_config_update(self, new_config: Dict[str, Any]):
        """Вызывается при обновлении конфигурации"""
        self.plugin_model.config = new_config
        self._load_config()  # перезагружаем с валидацией

    def on_device_scan(self, new_config: Dict[str, Any]):
        """Вызывается при обновлении конфигурации"""
        self.plugin_model.config = new_config
        self._load_config()  # перезагружаем с валидацией

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Валидация конфигурации перед сохранением.
        По умолчанию использует Pydantic модель.
        """
        try:
            self.config_class.model_validate(config)
            return True
        except Exception:
            return False

    @abstractmethod
    def set_sensor_value(
            self,
            external_id: str,
            capability: str,
            identifier: Optional[str],
            value: Any
    ) -> bool:
        """
        Установить значение сенсора.
        Вызывается DeviceManager'ом.
        Плагин сам решает, как отправить команду устройству.
        """
        pass
