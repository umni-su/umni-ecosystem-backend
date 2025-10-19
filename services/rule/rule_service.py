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

from classes.events.event_bus import event_bus
from classes.events.event_types import EventType
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from classes.rules.rule_execution_tracker import RuleExecutionTracker
from classes.rules.rule_executor import RuleExecutor
from classes.rules.rules_store import rules_triggers_store
from classes.thread.task_manager import TaskManager
from database.session import write_session
from entities.rule_entity import RuleNode
from models.camera_event_model import CameraEventModel
from models.device_model_relations import DeviceModelWithRelations
from models.rule_model import RuleNodeTypes, NodeVisualize, RuleNodeTypeKeys
from models.sensor_model import SensorModelWithDevice
from repositories.rules_repository import RulesRepository
from services.base_service import BaseService
from sqlmodel import select

"""
Сервис-класс обработки правил автоматизаций
с регистрацией подписки на события триггеров автоматизации
"""


class RuleService(BaseService):
    name = "rule"
    task_manager: TaskManager | None = None
    execution_tracker = RuleExecutionTracker()

    def run_execution_trigger(self, entity_id: int, trigger: RuleNodeTypeKeys):
        trigger_entity_id: int = entity_id

        exists = rules_triggers_store.find(key=trigger).exists(entity_id=trigger_entity_id)
        if exists:
            trigger_models = rules_triggers_store.find(key=trigger).find(entity_id=trigger_entity_id)
            for model in trigger_models:
                Logger.debug(
                    f"✅ Rule {model.rule_id} has entity {trigger_entity_id} with all ids: {model.ids}",
                    LoggerType.RULES
                )

                # Проверяем, не выполняется ли правило уже
                if self.execution_tracker.is_executing(model.rule_id):
                    Logger.warn(
                        f"⚠️ Rule {model.rule_id} is already executing, skipping",
                        LoggerType.RULES
                    )
                    continue

                rule = RulesRepository.get_rule(model.rule_id)
                self._execute_rule_with_tracking(rule, trigger_entity_id)
                break

    def run_execution_motion_start(self, event: CameraEventModel):
        self.run_execution_trigger(event.area_id, RuleNodeTypeKeys.MOTION_START)

    def run_execution_motion_end(self, event: CameraEventModel):
        self.run_execution_trigger(event.area_id, RuleNodeTypeKeys.MOTION_END)

    def run_device_change_state(self, device: DeviceModelWithRelations):
        self.run_execution_trigger(device.id, RuleNodeTypeKeys.DEVICES_CHANGES)

    def run_sensor_change_state(self, sensor: SensorModelWithDevice):
        self.run_execution_trigger(sensor.id, RuleNodeTypeKeys.SENSORS_CHANGES)

    def _execute_rule_with_tracking(self, rule, entity_id: int | None = None):
        """Запускает выполнение правила с отслеживанием статуса"""
        # Пытаемся пометить правило как выполняющееся
        if not self.execution_tracker.mark_executing(rule.id):
            Logger.warn(f"Rule {rule.id} is already executing, skipping", LoggerType.RULES)
            return

        try:
            # Запускаем выполнение в отдельном потоке или синхронно
            if RuleService.task_manager:
                # Обязательно передаем entity_id
                RuleService.task_manager.submit(
                    self._execute_rule,
                    rule=rule,
                    entity_id=entity_id
                )
            else:
                self._execute_rule(rule, entity_id)
        except Exception as e:
            # В случае ошибки при запуске снимаем блокировку
            self.execution_tracker.mark_completed(rule.id)
            raise e

    def _execute_rule(self, rule, entity_id: int | None = None):
        """Внутренний метод выполнения правила"""
        try:
            RuleExecutor(rule).execute(entity_id)
        finally:
            # Всегда снимаем блокировку после выполнения
            self.execution_tracker.mark_completed(rule.id)

    def run(self):
        with write_session() as session:
            orm_triggers: list[RuleNode] = session.exec(
                select(RuleNode).where(RuleNode.type == RuleNodeTypes.TRIGGER.value)
            ).all()
            triggers = [
                NodeVisualize.model_validate(
                    t.to_dict()
                ) for t in orm_triggers
            ]
            rules_triggers_store.reread(triggers)

        event_bus.subscribe(EventType.MOTION_START, self.run_execution_motion_start)
        event_bus.subscribe(EventType.MOTION_END, self.run_execution_motion_end)
        event_bus.subscribe(EventType.DEVICE_CHANGE_STATE, self.run_device_change_state)
        event_bus.subscribe(EventType.SENSOR_CHANGE_STATE, self.run_sensor_change_state)

        RuleService.task_manager = TaskManager(max_workers=2)
