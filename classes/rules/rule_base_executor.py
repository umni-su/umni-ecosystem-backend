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
from models.rule_model import NodeVisualize, NodeTriggerOptions


class RuleBaseExecutor:
    node: NodeVisualize
    ids: [int] = []
    key: str | None

    def __init__(self, node: NodeVisualize):
        self.node = node
        if isinstance(self.node.data.options, NodeTriggerOptions):
            try:
                self.key = self.node.data.flow.el.key
                self.ids = self.node.data.options.ids
            except Exception as e:
                self.key = None
                Logger.err('Key not assign to trigger', LoggerType.RULES)
