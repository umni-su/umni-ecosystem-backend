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
from typing import Any, Dict

from classes.thread.daemon import Daemon
from models.plugin_model import PluginModel, PluginConfigModel


class BasePlugin(ABC):
    """Абстрактный базовый класс для всех плагинов"""

    plugin_config_model: PluginConfigModel = PluginConfigModel()
    plugin_dir = "plugins"
    daemon: Daemon | None = None
    _is_running: bool = False

    def __init__(self, plugin_model: PluginModel):
        self.plugin_model = plugin_model
        self._is_running = False
        self._get_config()

    @classmethod
    def load_config(cls, name: str):
        config_file = os.path.join(cls.plugin_dir, "custom", name, f"{name}_config.json")
        print(config_file)
        if os.path.exists(os.path.abspath(config_file)):
            with open(config_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                cls.plugin_config_model = PluginConfigModel.model_validate(json_data)

    def _get_config(self):
        self.load_config(self.name)

    @property
    def name(self) -> str:
        return self.plugin_model.name

    @property
    def version(self) -> str:
        return self.plugin_model.version

    @property
    def is_running(self) -> bool:
        return self._is_running

    @abstractmethod
    def execute(self, data: Dict[str, Any] = None) -> Any:
        """Основной метод выполнения плагина"""
        pass

    def _run(self, data: Dict[str, Any] = None):
        self.daemon = Daemon(self.execute, data)

    def on_start(self):
        """Вызывается при запуске плагина"""
        if not self._is_running:
            self._is_running = True
            self._run()

    def on_stop(self):
        """Вызывается при остановке плагина"""
        self._is_running = False
        self.daemon = None

    def on_config_update(self, new_config: Dict[str, Any]):
        """Вызывается при обновлении конфигурации"""
        self.plugin_model.config = new_config

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Валидация конфигурации"""
        return True
