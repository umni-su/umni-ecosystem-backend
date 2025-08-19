from contextlib import contextmanager
from typing import Dict, List, Any, Iterator, Optional
import json
from sqlmodel import Session, select

from database.database import write_session
from entities.rule_entity import RuleEntity, RuleNode, RuleEdge
from models.rule_model import RuleNodeTypes, RuleEntityType, RuleNodeTypeKeys


class RuleExecutor:
    """Полнофункциональный обработчик правил автоматизации с контекстным управлением сессиями.

    Особенности:
    - Безопасное управление подключениями к БД
    - Поддержка всех типов узлов (триггеры, условия, сущности, действия)
    - Рекурсивный обход графа правил
    - Логирование выполнения (заглушки)
    """

    def __init__(self):
        """Инициализация исполнителя правил."""
        self._handle_sensor_entity = None
        self._handle_camera_entity = None
        self._handle_device_entity = None
        self.visited_nodes = set()  # Для отслеживания посещенных узлов

    @contextmanager
    def _get_session(self) -> Iterator[Session]:
        """Контекстный менеджер для получения сессии БД.

        Returns:
            Iterator[Session]: Сессия базы данных

        Example:
            with self._get_session() as session:
                # работа с сессией
        """
        with write_session() as session:
            yield session

    async def execute_from_start(self, rule_id: int) -> bool:
        """Выполняет правило автоматизации, начиная со START ноды.

        Args:
            rule_id (int): ID правила для выполнения

        Returns:
            bool: True если выполнение прошло успешно
        """
        with self._get_session() as session:
            rule = session.get(RuleEntity, rule_id)
            if not rule:
                raise ValueError(f"Rule {rule_id} not found")
            if not rule.enabled:
                return False

            nodes = session.exec(select(RuleNode).where(RuleNode.rule_id == rule_id)).all()
            edges = session.exec(select(RuleEdge).where(RuleEdge.rule_id == rule_id)).all()

            try:
                # Находим START ноду
                start_node = next((n for n in nodes if n.type == RuleNodeTypes.START), None)
                if not start_node:
                    raise ValueError("Rule has no START node")

                # Очищаем историю посещений
                self.visited_nodes.clear()

                # Получаем карту узлов
                node_map = {node.id: node for node in nodes}

                # Обрабатываем все связи из START ноды
                for edge in [e for e in edges if e.source == start_node.id]:
                    if next_node := node_map.get(edge.target):
                        await self._process_node(session, next_node, node_map, edges)

                return True
            except Exception as e:
                self._log_error(f"Error executing rule {rule_id} from START: {str(e)}")
                return False

    async def execute_rule(self, rule_id: int, trigger_data: Dict[str, Any]) -> bool:
        """Основной метод выполнения правила.

        Args:
            rule_id (int): ID правила для выполнения
            trigger_data (Dict[str, Any]): Данные триггерного события

        Returns:
            bool: True если выполнение прошло успешно

        Raises:
            ValueError: Если правило не найдено
        """
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

        # Очищаем историю посещений перед выполнением
        self.visited_nodes.clear()

        # Обрабатываем все триггеры, связанные со стартовым узлом
        for edge in [e for e in edges if e.source == start_node.id]:
            if trigger_node := node_map.get(edge.target):
                if self._check_trigger(trigger_node, trigger_data):
                    await self._process_node(session, trigger_node, node_map, edges)

    async def _process_node(
            self,
            session: Session,
            node: RuleNode,
            node_map: Dict[str, RuleNode],
            edges: List[RuleEdge],
            trigger_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Обновленная версия с поддержкой выполнения без триггера."""
        if node.id in self.visited_nodes:
            return
        self.visited_nodes.add(node.id)

        try:
            handlers = {
                RuleNodeTypes.TRIGGER: self._process_trigger_node,
                RuleNodeTypes.CONDITION: self._process_condition_node,
                RuleNodeTypes.ENTITY: self._process_entity_node,
                RuleNodeTypes.ACTION: self._process_action_node,
                RuleNodeTypes.START: self._process_start_node  # Новый обработчик
            }

            if handler := handlers.get(node.type):
                await handler(session, node, node_map, edges, trigger_data)
        except Exception as e:
            self._log_error(f"Error processing node {node.id}: {str(e)}")
            raise

    async def _process_start_node(
            self,
            session: Session,
            node: RuleNode,
            node_map: Dict[str, RuleNode],
            edges: List[RuleEdge],
            trigger_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Обработка START ноды - просто передаем управление дальше."""
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
            edges: List[RuleEdge]
    ) -> None:
        """Обработка узла-триггера."""
        self._log_debug(f"Processing trigger node {node.id}")
        next_edges = [e for e in edges if e.source == node.id]
        for edge in next_edges:
            if next_node := node_map.get(edge.target):
                await self._process_node(session, next_node, node_map, edges)

    def _validate_rule_structure(self, nodes: List[RuleNode], edges: List[RuleEdge]) -> bool:
        """Проверяет базовую структуру правила."""
        start_nodes = [n for n in nodes if n.type == RuleNodeTypes.START]
        if len(start_nodes) != 1:
            raise ValueError("Rule must have exactly one START node")

        # Дополнительные проверки...
        return True

    async def _process_condition_node(
            self,
            session: Session,
            node: RuleNode,
            node_map: Dict[str, RuleNode],
            edges: List[RuleEdge]
    ) -> None:
        """Обработка узла-условия с ветвлением."""
        node_data = json.loads(node.data)
        condition_result = self._evaluate_condition(session, node_data['options'])

        self._log_debug(f"Condition node {node.id} result: {condition_result}")

        for edge in [e for e in edges if e.source == node.id]:
            edge_type = edge.source_handle.split('-')[-1] if edge.source_handle else ''
            if (condition_result and edge_type == 'true') or (not condition_result and edge_type == 'false'):
                if next_node := node_map.get(edge.target):
                    await self._process_node(session, next_node, node_map, edges)

    async def _process_entity_node(
            self,
            session: Session,
            node: RuleNode,
            node_map: Dict[str, RuleNode],
            edges: List[RuleEdge]
    ) -> None:
        """Обработка узла-сущности (устройство/камера/сенсор)."""
        node_data = json.loads(node.data)
        options = node_data['options']

        self._log_debug(f"Processing entity node {node.id} of type {node.entity_type}")

        # Обработка в зависимости от типа сущности
        handlers = {
            RuleEntityType.DEVICE: self._handle_device_entity,
            RuleEntityType.CAMERA: self._handle_camera_entity,
            RuleEntityType.SENSOR: self._handle_sensor_entity
        }

        if handler := handlers.get(node.entity_type):
            await handler(session, node.entity_id, options)

        # Передаем управление дальше по графу
        next_edges = [e for e in edges if e.source == node.id]
        for edge in next_edges:
            if next_node := node_map.get(edge.target):
                await self._process_node(session, next_node, node_map, edges)

    async def _process_action_node(
            self,
            session: Session,
            node: RuleNode,
            node_map: Dict[str, RuleNode],
            edges: List[RuleEdge]
    ) -> None:
        """Выполнение конечного действия."""
        node_data = json.loads(node.data)
        action_key = node_data['flow']['el']['key']

        self._log_debug(f"Executing action {action_key} from node {node.id}")

        # Реализация конкретных действий
        actions = {
            RuleNodeTypeKeys.ALARM_ON: lambda: self._execute_alarm(session, on=True),
            RuleNodeTypeKeys.ALARM_OFF: lambda: self._execute_alarm(session, on=False),
            RuleNodeTypeKeys.ACTION_EMAIL: lambda: self._send_email(session, node_data['options']),
            RuleNodeTypeKeys.ACTION_TELEGRAM: lambda: self._send_telegram(session, node_data['options']),
            RuleNodeTypeKeys.ACTION_WEBHOOK: lambda: self._send_webhook(session, node_data['options'])
        }

        if action := actions.get(action_key):
            await action()

    # Реализации конкретных обработчиков действий
    async def _execute_alarm(self, session: Session, on: bool) -> None:
        """Управление тревожной сигнализацией."""
        self._log_info(f"Setting alarm state to {'ON' if on else 'OFF'}")
        # Реальная реализация здесь...

    async def _send_email(self, session: Session, options: Dict[str, Any]) -> None:
        """Отправка email-уведомления."""
        self._log_info(f"Sending email to {options.get('to')}")
        # Реальная реализация здесь...

    # Вспомогательные методы
    def _check_trigger(self, node: RuleNode, trigger_data: Dict[str, Any]) -> bool:
        """Проверка соответствия триггера входящим данным."""
        node_data = json.loads(node.data)
        trigger_key = node_data['flow']['el']['key']

        # Проверка соответствия сущности
        if node.entity_id != trigger_data.get('entity_id'):
            return False

        # Логика проверки для разных типов триггеров
        trigger_checks = {
            RuleNodeTypeKeys.SENSORS_CHANGES: lambda: (
                    trigger_data.get('entity_type') == RuleEntityType.SENSOR and
                    trigger_data.get('event') == 'state_change'
            ),
            RuleNodeTypeKeys.MOTION_START: lambda: (
                    trigger_data.get('entity_type') == RuleEntityType.CAMERA and
                    trigger_data.get('event') == 'motion_start'
            ),
            RuleNodeTypeKeys.DEVICES_CHANGES: lambda: (
                    trigger_data.get('entity_type') == RuleEntityType.DEVICE and
                    trigger_data.get('event') in ['state_change', 'turn_on', 'turn_off']
            )
        }

        return trigger_key in trigger_checks and trigger_checks[trigger_key]()

    def _evaluate_condition(self, session: Session, options: Dict[str, Any]) -> bool:
        """Вычисление результата условия."""
        if not options.get('items'):
            return True

        results = []
        for item in options['items']:
            current_value = self._get_entity_value(session, item['entity_id'])
            results.append(self._compare_values(current_value, item['operator'], item['value']))

        return all(results) if options.get('operand') == 'and' else any(results)

    def _get_entity_value(self, session: Session, entity_id: int) -> Any:
        """Получение текущего значения сущности."""
        # В реальной реализации - запрос к API или БД
        return 0  # Заглушка

    def _compare_values(self, current: Any, operator: str, target: Any) -> bool:
        """Сравнение значений по оператору."""
        ops = {
            '>': lambda a, b: a > b,
            '<': lambda a, b: a < b,
            '>=': lambda a, b: a >= b,
            '<=': lambda a, b: a <= b,
            '==': lambda a, b: a == b,
            '!=': lambda a, b: a != b
        }
        return ops.get(operator, lambda a, b: False)(current, target)

    # Методы логирования (заглушки)
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
