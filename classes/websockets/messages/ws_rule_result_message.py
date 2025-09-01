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

from pydantic import Field, computed_field
from classes.rules.rule_executor import RuleExecutor
from classes.websockets.messages.ws_message_base import WebsocketMessageBase
from classes.websockets.ws_message_topic import WebsocketMessageTopicEnum


class WebsocketMessageRuleResult(WebsocketMessageBase):
    topic: WebsocketMessageTopicEnum | None = WebsocketMessageTopicEnum.RULE_EXECUTED

    executor: RuleExecutor = Field(exclude=True)

    def __init__(self, executor: RuleExecutor):
        super().__init__()
        self.executor = executor

    @computed_field
    @property
    def rule(self) -> dict:
        return {
            "rule_id": self.executor.rule.id,
            "nodes": self.executor.rule.nodes,
            "edges": self.executor.rule.edges
        }

    class Config:
        arbitrary_types_allowed = True
