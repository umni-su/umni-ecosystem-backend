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

from classes.l10n.l10n import translator, plugin_translate
from classes.thread.daemon import Daemon
from classes.ui.ui_form_generator import UIEnhancedModel
from models.plugin_model import PluginModel, PluginConfigModel
from fastapi import Request


class BasePluginConfig(UIEnhancedModel):
    pass


class BasePlugin(ABC):
    """Абстрактный базовый класс для всех плагинов"""

    plugin_config_model: PluginConfigModel = PluginConfigModel()
    plugin_dir = "plugins"
    daemon: Daemon | None = None
    _is_running: bool = False
    _translate_func = None
    plugin_name = None

    def __init__(self, plugin_model: PluginModel, plugin_config: BasePluginConfig | None = None):
        self.plugin_model = plugin_model
        self._is_running = False
        self._get_config()
        self.config = plugin_config

    @classmethod
    def translate(cls, message: str, **kwargs) -> str:
        """Статический метод для переводов в конфигах"""
        if cls.plugin_name:
            from classes.l10n.l10n import plugin_translate
            return plugin_translate(
                plugin_name=cls.plugin_name,
                message=message,
                **kwargs
            )

        # Fallback
        if kwargs:
            try:
                return message.format(**kwargs)
            except (KeyError, ValueError):
                return message
        return message

    def _(self, message: str, **kwargs) -> str:
        """Функция перевода для плагина"""
        if self.plugin_name:
            result = plugin_translate(
                plugin_name=self.plugin_name,
                message=message,
                **kwargs
            )
            return result

        # Fallback
        if kwargs:
            try:
                return message.format(**kwargs)
            except (KeyError, ValueError):
                return message
        return message

    def get_current_language(self) -> str:
        """Получить текущий язык"""
        return translator.get_default_lang()

    @classmethod
    def load_config(cls, name: str):
        config_file = os.path.join(cls.plugin_dir, "custom", name, f"{name}_config.json")
        if os.path.exists(os.path.abspath(config_file)):
            with open(config_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                cls.plugin_config_model = PluginConfigModel.model_validate(json_data)
            cls.set_configuration()

    def _get_config(self):
        self.load_config(self.name)

    @classmethod
    @abstractmethod
    def set_configuration(cls):
        pass

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
