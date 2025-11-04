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
from urllib import request
from typing import Optional, Dict, Any

from classes.logger.logger import Logger
from classes.rules.rule_base_executor import RuleBaseExecutor
from models.rule_model import NodeActionOptions, NodeActionWebhookOptions


class ActionWebhookExecutor(RuleBaseExecutor):
    def execute(self):
        if isinstance(self.node.data.options, NodeActionOptions):
            action: NodeActionWebhookOptions = self.node.data.options.action
            if action.url is not None:
                self.send_webhook(
                    url=action.url,
                    method='GET',
                )
            Logger.debug(f'Webhook executed successfully for {action.url}')

    def send_webhook(
            self,
            url: str,
            method: str = "POST",
            body: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Возвращает True если успешно, False если ошибка
        """
        try:
            # Подготовка запроса
            data = None
            if body:
                data = json.dumps(body).encode('utf-8')

            # Базовые заголовки
            default_headers = {"Content-Type": "application/json"}
            if headers:
                default_headers.update(headers)

            # Создание запроса
            req = request.Request(
                url=url,
                data=data,
                headers=default_headers,
                method=method
            )

            # Выполнение запроса
            with request.urlopen(req, timeout=30) as response:
                return response.getcode() == 200

        except Exception:
            return False
