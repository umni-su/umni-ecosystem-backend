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

from typing import Set
from threading import Lock


class RuleExecutionTracker:
    def __init__(self):
        self._executing_rules: Set[int] = set()
        self._lock = Lock()

    def is_executing(self, rule_id: int) -> bool:
        """Проверяет, выполняется ли правило в данный момент"""
        with self._lock:
            return rule_id in self._executing_rules

    def mark_executing(self, rule_id: int) -> bool:
        """
        Помечает правило как выполняющееся.
        Возвращает True если удалось пометить (правило не выполнялось),
        False если правило уже выполняется.
        """
        with self._lock:
            if rule_id in self._executing_rules:
                return False
            self._executing_rules.add(rule_id)
            return True

    def mark_completed(self, rule_id: int) -> None:
        """Помечает правило как завершенное"""
        with self._lock:
            self._executing_rules.discard(rule_id)
