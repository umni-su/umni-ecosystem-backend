#  Copyright (C) 2025 Mikhail Sazanov
#  #
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#  #
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#  #
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

from enum import Enum

from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from models.rule_model import RuleModel, NodeVisualize


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


'''
Usage
_json = json.loads(content)
rule_model = RuleModel.model_validate_json(content)
exec = RuleExecutor(rule_model)
exec.parse_rule()
print(exec.res.model_dump_json(indent=2))
print([n.model_dump_json() for n in exec.nodes])
print([e.model_dump_json() for e in exec.edges])
'''


class RuleExecutor:
    nodes = []
    edges = []
    res = []

    def __init__(self, rule: RuleModel):
        self.rule: RuleModel = rule
        self.start_node = None

    def parse_rule(self):
        self.nodes = self.rule.nodes
        self.edges = self.rule.edges
        Logger.debug(f"Parsing rule, loads {len(self.nodes)} nodes and {len(self.edges)} edges", LoggerType.RULES)
        self.start_node = self.find_start_node()
        self.res = self.parse_recursive(self.start_node)

    def find_node_by_id(self, id: str):
        n = [(index, node) for index, node in enumerate(self.nodes) if node.id == id]
        if n:
            return n[0]
        else:
            return None

    def find_start_node(self):
        for node in self.nodes:
            if node.type == 'start':
                Logger.debug(f'Founded start node: {node.id}', LoggerType.RULES)
                return node
        return None

    def parse_recursive(self, node: NodeVisualize):
        node.children = []
        res_data = node
        result: bool = False
        if node.type == 'condition':
            result = self.execute_condition(node)

        Logger.debug(f"Parsing node: {node.id} {node.data.flow.el.key}", LoggerType.RULES)

        _edges = [(i, e) for i, e in enumerate(self.edges) if e.source == node.id]
        Logger.debug(f'Found {len(_edges)}', LoggerType.RULES)

        for edge in _edges:

            Logger.debug(f'Found edge: {edge[1].source_handle}', LoggerType.RULES)

            if edge[1].source_handle == 'output-true':  # <-------------------- применение стиля к визуалу
                self.edges[edge[0]].animated = result

            index, founded_node_by_edge = self.find_node_by_id(edge[1].target)
            if isinstance(founded_node_by_edge, NodeVisualize):
                print(f'[{node.type.upper()} {node.data.flow.el.key}] Found node: {founded_node_by_edge.id}')
                parse_recursive = self.parse_recursive(founded_node_by_edge)
                parse_recursive.source = edge[1].source_handle
                res_data.children.append(parse_recursive)
            else:
                Logger.debug(f'Cannot find next by relative node: {node.id}', LoggerType.RULES)
        return res_data

    def execute_condition(self, node: NodeVisualize):
        return node.type == 'condition'
