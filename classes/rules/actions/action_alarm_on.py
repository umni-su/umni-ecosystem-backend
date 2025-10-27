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
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from classes.rules.rule_base_executor import RuleBaseExecutor


class ActionAlarmOnExecutor(RuleBaseExecutor):
    def execute(self):
        Logger.info(f"Sending email - {self.node.data}", LoggerType.RULES)
        # Реализация включения сигнализации
        # Например: self._alarm_system.turn_on()
