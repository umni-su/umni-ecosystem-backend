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
import random
from enum import Enum

from classes.events.event_bus import event_bus
from classes.events.event_types import EventType
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from classes.rules.rule_action_executor import RuleActionExecutor
from classes.rules.rule_condition_executor import RuleConditionExecutor
from classes.rules.rules_store import rules_triggers_store
from models.rule_model import RuleModel, NodeVisualize, EdgeStyle


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
    test: bool = False
    trigger_entity_id: int | None = None

    def __init__(self, rule: RuleModel, test: bool = False):
        self.rule: RuleModel = rule
        self.start_node = None
        self.test = test

    def set_trigger_id(self, trigger_id: int):
        self.trigger_entity_id = trigger_id
        return self

    def execute(self, trigger_id: int | None = None):
        self.trigger_entity_id = trigger_id
        self.nodes = self.rule.nodes
        self.edges = self.rule.edges
        Logger.debug(f"Parsing rule, loads {len(self.nodes)} nodes and {len(self.edges)} edges", LoggerType.RULES)
        self.start_node = self.find_start_node()
        self.res = self.parse_recursive(self.start_node)

        event_bus.publish(EventType.RULE_EXECUTED, rule_id=self.rule.id, nodes=self.nodes, edges=self.edges)

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

        # Выполняем проверку для разных типов узлов
        if node.type == 'condition':
            result = self.execute_condition(node)
            Logger.debug(f"Condition node {node.id} result: {result}", LoggerType.RULES)
        elif node.type == 'trigger':
            result = self.execute_trigger(node)
            Logger.debug(f"Trigger node {node.id} result: {result}", LoggerType.RULES)
            # Если триггер не сработал, не идем дальше
            if not result:
                Logger.debug(f"Trigger {node.id} failed, stopping execution", LoggerType.RULES)
                return res_data
        elif node.type == 'action':
            self.execute_action(node)

        Logger.debug(f"Parsing node: {node.id} {node.data.flow.el.key}", LoggerType.RULES)

        _edges = [(i, e) for i, e in enumerate(self.edges) if e.source == node.id]
        Logger.debug(f'Found {len(_edges)} edges from node {node.id}', LoggerType.RULES)

        for edge in _edges:
            edge_id, edge_data = edge

            # Определяем, нужно ли обрабатывать этот edge
            should_process = False
            edge_type = None

            if node.type == 'condition':
                # Для condition-узлов обрабатываем только соответствующую ветку
                if edge_data.source_handle == 'output-true' and result:
                    should_process = True
                    edge_type = 'true'
                    # Применяем стиль для визуализации
                    self.edges[edge_id].animated = True
                    self.edges[edge_id].style = EdgeStyle(stroke="green", strokeWidth=3)
                elif edge_data.source_handle == 'output-false' and not result:
                    should_process = True
                    edge_type = 'false'
                    # Применяем стиль для визуализации
                    self.edges[edge_id].animated = True
                    self.edges[edge_id].style = EdgeStyle(stroke="red", strokeWidth=3)
            else:
                # Для не-condition узлов обрабатываем все edges только если результат True
                # (для trigger - если он сработал, для других типов - всегда)
                if node.type == 'trigger':
                    should_process = result
                    # Если триггер сработал - раскрашиваем edge в фиолетовый
                    if result:
                        self.edges[edge_id].animated = True
                        self.edges[edge_id].style = EdgeStyle(stroke="purple", strokeWidth=3)
                        Logger.debug(f'Trigger edge styled: purple', LoggerType.RULES)
                else:
                    should_process = True
                edge_type = 'default'

            if should_process:
                Logger.debug(f'Processing {edge_type} edge: {edge_data.source_handle}', LoggerType.RULES)

                index, founded_node_by_edge = self.find_node_by_id(edge_data.target)
                if isinstance(founded_node_by_edge, NodeVisualize):
                    # print(f'[{node.type.upper()} {node.data.flow.el.key}] Found next node: {founded_node_by_edge.id}')
                    parse_recursive = self.parse_recursive(founded_node_by_edge)
                    parse_recursive.source = edge_data.source_handle
                    res_data.children.append(parse_recursive)
                else:
                    Logger.debug(f'Cannot find next node for edge: {edge_data.id}', LoggerType.RULES)

        return res_data

    def execute_condition(self, node: NodeVisualize):
        # print(node.model_dump_json(indent=2))
        return RuleConditionExecutor(node).execute()

    def execute_trigger(self, node: NodeVisualize):
        # Skip checking trigger when testing request
        if self.test:
            return True

        return rules_triggers_store.find(node.key).exists(
            self.trigger_entity_id
        )

    def execute_action(self, node: NodeVisualize):
        RuleActionExecutor(node).execute()
