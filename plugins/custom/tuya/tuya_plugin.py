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

from plugins.base_plugin import BasePlugin
from typing import Any, Dict
import tinytuya


class TuyaPlugin(BasePlugin):
    """Пример плагина-шаблона"""

    def execute(self, data: Dict[str, Any] = None) -> Any:
        """Основная логика плагина"""
        if not self._is_running:
            raise RuntimeError("Plugin is not running")

        # Пример обработки данных
        result = {
            "processed": True,
            "plugin": self.name,
            "input_data": data,
            "config": self._config
        }

        print(result)

        return result

    def on_start(self):
        super().on_start()
        # Инициализация плагина
        self._config = self.plugin_model.config or {}
        print(f"Plugin {self.name} started")

    def on_stop(self):
        super().on_stop()
        # Очистка ресурсов
        print(f"Plugin {self.name} stopped")

    def on_config_update(self, new_config: Dict[str, Any]):
        super().on_config_update(new_config)
        self._config = new_config

    def validate_config(self, config: Dict[str, Any]) -> bool:
        required_fields = ["api_key", "endpoint"]  # Пример обязательных полей
        return all(field in config for field in required_fields)
