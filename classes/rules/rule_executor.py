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

from contextlib import contextmanager
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Iterator, Optional
import json
from sqlmodel import Session, select

from database.session import write_session
from entities.rule_entity import RuleEntity, RuleNode, RuleEdge
from models.rule_model import RuleNodeTypes, RuleEntityType, RuleNodeTypeKeys
from pydantic import BaseModel, Field


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class ExecutionStep(BaseModel):
    node_id: str
    node_type: str
    status: ExecutionStatus
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None
    duration_ms: Optional[int] = None


class ExecutionResult(BaseModel):
    execution_id: str
    rule_id: int
    status: ExecutionStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    total_duration_ms: Optional[int] = None
    steps: List[ExecutionStep] = []  # Исправлено!
    trigger_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class RuleExecutor:
    """Полнофункциональный обработчик правил автоматизации с контекстным управлением сессиями."""

    def __init__(self):
        self.visited_nodes = set()

    @contextmanager
    def _get_session(self) -> Iterator[Session]:
        with write_session() as session:
            yield session

    async def execute_from_start(self, rule_id: int) -> ExecutionResult:
        """Выполняет правило с START ноды, имитируя срабатывание триггера."""
        execution_id = f"exec_{datetime.now().timestamp()}_{rule_id}"
        start_time = datetime.utcnow()

        self.execution_result = ExecutionResult(
            execution_id=execution_id,
            rule_id=rule_id,
            status=ExecutionStatus.PENDING,
            start_time=start_time,
            steps=[]
        )

        try:
            with self._get_session() as session:
                rule = session.get(RuleEntity, rule_id)
                if not rule:
                    raise ValueError(f"Rule {rule_id} not found")
                if not rule.enabled:
                    self._add_step("rule_check", "RULE", ExecutionStatus.SKIPPED,
                                   {"reason": "Rule is disabled"})
                    self.execution_result.status = ExecutionStatus.SKIPPED
                    return self.execution_result

                nodes = session.exec(select(RuleNode).where(RuleNode.rule_id == rule_id)).all()
                edges = session.exec(select(RuleEdge).where(RuleEdge.rule_id == rule_id)).all()

                start_node = next((n for n in nodes if n.type == RuleNodeTypes.START), None)
                if not start_node:
                    raise ValueError("Rule has no START node")

                self.visited_nodes.clear()
                node_map = {node.id: node for node in nodes}

                # Добавляем информацию о START ноде (без деталей триггера)
                self._add_step(start_node.id, start_node.type, ExecutionStatus.SUCCESS)

                # Обрабатываем все связи из START ноды
                for edge in [e for e in edges if e.source == start_node.id]:
                    if next_node := node_map.get(edge.target):
                        # Для execute_from_start имитируем срабатывание триггера
                        fake_trigger_data = self._generate_fake_trigger_data(next_node)
                        await self._process_node(session, next_node, node_map, edges, fake_trigger_data)

                self.execution_result.status = ExecutionStatus.SUCCESS

        except Exception as e:
            self.execution_result.status = ExecutionStatus.FAILED
            self.execution_result.error_message = str(e)
            self._add_step("error", "ERROR", ExecutionStatus.FAILED, {"error": str(e)})

        finally:
            end_time = datetime.utcnow()
            self.execution_result.end_time = end_time
            self.execution_result.total_duration_ms = int(
                (end_time - start_time).total_seconds() * 1000
            )

        return self.execution_result

    def _generate_fake_trigger_data(self, trigger_node: RuleNode) -> Dict[str, Any]:
        """Генерирует фиктивные данные триггера для тестового выполнения."""
        node_data = self._get_node_data(trigger_node)
        trigger_key = node_data.get('flow', {}).get('el', {}).get('key', '')

        # Определяем тип сущности по ключу триггера
        entity_type_mapping = {
            "sensors.changes.state": RuleEntityType.SENSOR,
            "camera.motion.start": RuleEntityType.CAMERA,
            "camera.motion.end": RuleEntityType.CAMERA,
            "devices.changes.state": RuleEntityType.DEVICE
        }

        return {
            "event": "state_change",
            "entity_id": trigger_node.entity_id or 1,  # Используем entity_id из узла если есть
            "entity_type": entity_type_mapping.get(trigger_key, RuleEntityType.SENSOR),
            "new_value": 25.5,
            "old_value": 20.0,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def execute_rule(self, rule_id: int, trigger_data: Dict[str, Any]) -> bool:
        """Основной метод выполнения правила."""
        with self._get_session() as session:
            rule = session.get(RuleEntity, rule_id)
            if not rule:
                raise ValueError(f"Rule {rule_id} not found")
            if not rule.enabled:
                return False

            nodes = session.exec(select(RuleNode).where(RuleNode.rule_id == rule_id)).all()
            edges = session.exec(select(RuleEdge).where(RuleEdge.rule_id == rule_id)).all()

            try:
                await self._process_rule(session, nodes, edges, trigger_data)
                return True
            except Exception as e:
                self._log_error(f"Error executing rule {rule_id}: {str(e)}")
                return False

    async def _process_rule(
            self,
            session: Session,
            nodes: List[RuleNode],
            edges: List[RuleEdge],
            trigger_data: Dict[str, Any]
    ) -> None:
        """Обработка графа правила."""
        node_map = {node.id: node for node in nodes}
        start_node = next((n for n in nodes if n.key == RuleNodeTypeKeys.RULE_START), None)

        if not start_node:
            self._log_warning("Rule has no start node")
            return

        self.visited_nodes.clear()

        for edge in [e for e in edges if e.source == start_node.id]:
            if trigger_node := node_map.get(edge.target):
                if self._check_trigger(trigger_node, trigger_data):
                    await self._process_node(session, trigger_node, node_map, edges, trigger_data)

    def _add_step(self, node_id: str, node_type: str, status: ExecutionStatus,
                  details: Optional[Dict] = None):
        """Добавляет шаг выполнения в результат."""
        current_time = datetime.utcnow()

        # Рассчитываем длительность предыдущего шага
        if self.execution_result.steps and self.current_step_start:
            last_step = self.execution_result.steps[-1]
            last_step.duration_ms = int((current_time - self.current_step_start).total_seconds() * 1000)

        step = ExecutionStep(
            node_id=node_id,
            node_type=node_type,
            status=status,
            timestamp=current_time,
            details=details,
            duration_ms=None  # Будет установлено при добавлении следующего шага
        )
        self.execution_result.steps.append(step)
        self.current_step_start = current_time

    async def _process_node(
            self,
            session: Session,
            node: RuleNode,
            node_map: Dict[str, RuleNode],
            edges: List[RuleEdge],
            trigger_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Рекурсивная обработка узла с трейсингом."""
        if node.id in self.visited_nodes:
            self._add_step(node.id, node.type, ExecutionStatus.SKIPPED,
                           {"reason": "Already visited"})
            return

        self.visited_nodes.add(node.id)

        # Создаем шаг для этого узла
        self._add_step(node.id, node.type, ExecutionStatus.PENDING)

        try:
            handlers = {
                RuleNodeTypes.TRIGGER: self._process_trigger_node,
                RuleNodeTypes.CONDITION: self._process_condition_node,
                RuleNodeTypes.ENTITY: self._process_entity_node,
                RuleNodeTypes.ACTION: self._process_action_node,
                RuleNodeTypes.START: self._process_start_node
            }

            if handler := handlers.get(node.type):
                await handler(session, node, node_map, edges, trigger_data)

            # Обновляем статус шага на успешный
            if self.execution_result.steps:
                self.execution_result.steps[-1].status = ExecutionStatus.SUCCESS

        except Exception as e:
            # Обновляем статус шага на неудачный
            if self.execution_result.steps:
                self.execution_result.steps[-1].status = ExecutionStatus.FAILED
                self.execution_result.steps[-1].details = {
                    "error": str(e),
                    **self.execution_result.steps[-1].details
                } if self.execution_result.steps[-1].details else {"error": str(e)}
            raise

    # Все методы обработки теперь принимают одинаковые аргументы
    async def _process_start_node(
            self,
            session: Session,
            node: RuleNode,
            node_map: Dict[str, RuleNode],
            edges: List[RuleEdge],
            trigger_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Обработка START ноды."""
        self._log_debug(f"Processing START node {node.id}")
        next_edges = [e for e in edges if e.source == node.id]
        for edge in next_edges:
            if next_node := node_map.get(edge.target):
                await self._process_node(session, next_node, node_map, edges, trigger_data)

    async def _process_trigger_node(
            self,
            session: Session,
            node: RuleNode,
            node_map: Dict[str, RuleNode],
            edges: List[RuleEdge],
            trigger_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Обработка узла-триггера с детальным логированием."""
        self._log_debug(f"Processing trigger node {node.id}")

        # Проверяем срабатывание триггера
        trigger_matched = self._check_trigger(node, trigger_data) if trigger_data else True

        # Добавляем детали проверки триггера в КОНЕЦ списка (текущий шаг)
        trigger_details = {
            "trigger_matched": trigger_matched,
            "trigger_data": trigger_data,
            "node_key": self._get_node_data(node).get('flow', {}).get('el', {}).get('key', 'unknown')
        }

        # Обновляем детали текущего шага (который был создан в _process_node)
        if self.execution_result.steps:
            self.execution_result.steps[-1].details = trigger_details

        if trigger_matched:
            # Если триггер сработал, продолжаем выполнение
            next_edges = [e for e in edges if e.source == node.id]
            for edge in next_edges:
                if next_node := node_map.get(edge.target):
                    await self._process_node(session, next_node, node_map, edges, trigger_data)
        else:
            self._log_debug(f"Trigger {node.id} did not match, stopping execution")

    async def _process_condition_node(
            self,
            session: Session,
            node: RuleNode,
            node_map: Dict[str, RuleNode],
            edges: List[RuleEdge],
            trigger_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Обработка узла-условия с ветвлением."""
        node_data = self._get_node_data(node)
        condition_result = self._evaluate_condition(session, node_data.get('options', {}))

        # Добавляем детали проверки условия
        condition_details = {
            "result": condition_result,
            "operand": node_data.get('options', {}).get('operand'),
            "items": node_data.get('options', {}).get('items', [])
        }
        self.execution_result.steps[-1].details = condition_details

        for edge in [e for e in edges if e.source == node.id]:
            edge_type = edge.source_handle.split('-')[-1] if edge.source_handle else ''
            if (condition_result and edge_type == 'true') or (not condition_result and edge_type == 'false'):
                if next_node := node_map.get(edge.target):
                    await self._process_node(session, next_node, node_map, edges, trigger_data)

    async def _process_entity_node(
            self,
            session: Session,
            node: RuleNode,
            node_map: Dict[str, RuleNode],
            edges: List[RuleEdge],
            trigger_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Обработка узла-сущности."""
        node_data = self._get_node_data(node)
        options = node_data.get('options', {})

        self._log_debug(f"Processing entity node {node.id} of type {node.entity_type}")

        # Добавляем детали обработки сущности
        entity_details = {
            "options": options,
            "entity_type": node.entity_type,
            "entity_id": node.entity_id
        }
        self.execution_result.steps[-1].details = entity_details

        handlers = {
            RuleEntityType.DEVICE: self._handle_device_entity,
            RuleEntityType.CAMERA: self._handle_camera_entity,
            RuleEntityType.SENSOR: self._handle_sensor_entity
        }

        if handler := handlers.get(node.entity_type):
            await handler(session, node.entity_id, options)

        next_edges = [e for e in edges if e.source == node.id]
        for edge in next_edges:
            if next_node := node_map.get(edge.target):
                await self._process_node(session, next_node, node_map, edges, trigger_data)

    async def _process_action_node(
            self,
            session: Session,
            node: RuleNode,
            node_map: Dict[str, RuleNode],
            edges: List[RuleEdge],
            trigger_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Выполнение конечного действия."""
        node_data = self._get_node_data(node)
        action_key = node_data.get('flow', {}).get('el', {}).get('key')

        self._log_debug(f"Executing action {action_key} from node {node.id}")

        # Добавляем детали действия
        action_details = {
            "action_key": action_key,
            "options": node_data.get('options', {})
        }
        self.execution_result.steps[-1].details = action_details

        actions = {
            "action.alarm.on": lambda: self._execute_alarm(session, on=True),
            "action.alarm.off": lambda: self._execute_alarm(session, on=False),
            "action.email": lambda: self._send_email(session, node_data.get('options', {})),
            "action.telegram": lambda: self._send_telegram(session, node_data.get('options', {})),
            "action.webhook": lambda: self._send_webhook(session, node_data.get('options', {}))
        }

        if action := actions.get(action_key):
            await action()

    # Остальные методы остаются без изменений
    async def _execute_alarm(self, session: Session, on: bool) -> None:
        self._log_info(f"Setting alarm state to {'ON' if on else 'OFF'}")

    async def _send_email(self, session: Session, options: Dict[str, Any]) -> None:
        self._log_info(f"Sending email to {options.get('to')}")

    def _get_node_data(self, node: RuleNode) -> Dict[str, Any]:
        """Безопасно извлекает данные узла, обрабатывая как строки JSON, так и словари."""
        try:
            if node.data is None:
                return {}
            elif isinstance(node.data, dict):
                return node.data
            elif isinstance(node.data, str):
                return json.loads(node.data)
            else:
                self._log_error(f"Unexpected data type in node {node.id}: {type(node.data)}")
                return {}
        except Exception as e:
            self._log_error(f"Error parsing data from node {node.id}: {str(e)}")
            return {}

    def _check_trigger(self, node: RuleNode, trigger_data: Dict[str, Any]) -> bool:
        """Проверка соответствия триггера входящим данным."""
        if not trigger_data:
            return True  # Если данных нет, считаем что триггер сработал

        # Проверяем, является ли data уже словарем или JSON строкой
        if isinstance(node.data, dict):
            node_data = node.data
        else:
            try:
                node_data = self._get_node_data(node)
            except (json.JSONDecodeError, TypeError):
                self._log_error(f"Invalid JSON data in node {node.id}: {node.data}")
                return False

        trigger_key = node_data['flow']['el']['key']

        # Проверка соответствия сущности (если указана в узле)
        if node.entity_id and node.entity_id != trigger_data.get('entity_id'):
            return False

        # Логика проверки для разных типов триггеров
        trigger_checks = {
            "sensors.changes.state": lambda: (
                    trigger_data.get('entity_type') == RuleEntityType.SENSOR and
                    trigger_data.get('event') == 'state_change'
            ),
            "camera.motion.start": lambda: (
                    trigger_data.get('entity_type') == RuleEntityType.CAMERA and
                    trigger_data.get('event') == 'motion_start'
            ),
            "camera.motion.end": lambda: (
                    trigger_data.get('entity_type') == RuleEntityType.CAMERA and
                    trigger_data.get('event') == 'motion_end'
            ),
            "devices.changes.state": lambda: (
                    trigger_data.get('entity_type') == RuleEntityType.DEVICE and
                    trigger_data.get('event') in ['state_change', 'turn_on', 'turn_off']
            )
        }

        return trigger_key in trigger_checks and trigger_checks[trigger_key]()

    def _evaluate_condition(self, session: Session, options: Dict[str, Any]) -> bool:
        if not options.get('items'):
            return True

        results = []
        for item in options['items']:
            current_value = self._get_entity_value(session, item['entity_id'])
            results.append(self._compare_values(current_value, item['operator'], item['value']))

        return all(results) if options.get('operand') == 'and' else any(results)

    def _get_entity_value(self, session: Session, entity_id: int) -> Any:
        return 0

    def _compare_values(self, current: Any, operator: str, target: Any) -> bool:
        ops = {
            '>': lambda a, b: a > b,
            '<': lambda a, b: a < b,
            '>=': lambda a, b: a >= b,
            '<=': lambda a, b: a <= b,
            '==': lambda a, b: a == b,
            '!=': lambda a, b: a != b
        }
        return ops.get(operator, lambda a, b: False)(current, target)

    def _log_debug(self, message: str) -> None:
        print(f"[DEBUG] {message}")

    def _log_info(self, message: str) -> None:
        print(f"[INFO] {message}")

    def _log_warning(self, message: str) -> None:
        print(f"[WARNING] {message}")

    def _log_error(self, message: str) -> None:
        print(f"[ERROR] {message}")

    def _send_telegram(self, session, param):
        pass

    def _send_webhook(self, session, param):
        pass

    def _handle_device_entity(self, session, entity_id, options):
        pass

    def _handle_camera_entity(self, session, entity_id, options):
        pass

    def _handle_sensor_entity(self, session, entity_id, options):
        pass
