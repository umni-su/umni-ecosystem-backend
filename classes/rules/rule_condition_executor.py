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
from classes.rules.rule_base_executor import RuleBaseExecutor
from classes.rules.rule_conditions import RuleAvailability, RuleComparison, RuleConditionGroupKey, RuleOperand, \
    RuleConditionKey
from models.rule_model import NodeConditionOptions, RuleNodeConditionDetailsItem, NodeConditionActionAvailable
from repositories.device_repository import DeviceRepository


class RuleConditionExecutor(RuleBaseExecutor):
    def execute(self):
        if isinstance(self.node.data.options, NodeConditionOptions):
            condition_result = False
            # Выполняем все блоки условий, они все должны вернуть True
            for condition in self.node.data.options.conditions:
                if (
                        condition.group == RuleConditionGroupKey.AVAILABILITY.value and
                        condition.key == RuleConditionKey.AVAILABILITY_DEVICE.value
                ):
                    condition_result = self.availability_device(
                        condition.operand,
                        condition.action.state,
                        condition.items
                    )
                    # Если хотя бы один блок вернет False, выполнение условия тоже возвращает False
                    if not condition_result:
                        return False
                else:
                    return False
            return condition_result
        return False

    """
    Device availability condition
    """

    @classmethod
    def availability_device(
            cls,
            operand: str,
            state: RuleAvailability,
            items: list[RuleNodeConditionDetailsItem]
    ):
        # RuleAvailability.ONLINE
        # RuleComparison.GREATER_THAN.value
        # print("\r\n", RuleOperand(operand), RuleAvailability(state), items, "\r\n")

        # Все устройства должны иметь такой же статус, что и ы state
        if operand == RuleOperand.AND.value:
            success = False
            for item in items:
                device = DeviceRepository.get_device(item.id)
                success = device.online == (state == RuleAvailability.ONLINE.value)
                if not success:
                    return False
            return success
        # Одно из устройств должно иметь статус, равный state
        elif operand == RuleOperand.OR.value:
            for item in items:
                device = DeviceRepository.get_device(item.id)
                if device.online == (state == RuleAvailability.ONLINE.value):
                    return True
            return False
        # Ни одно из устройств не должно иметь статус state
        elif operand == RuleOperand.NOT.value:
            success = False
            for item in items:
                device = DeviceRepository.get_device(item.id)
                success = device.online != (state == RuleAvailability.ONLINE.value)
                if not success:
                    return False
            return success
