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

import operator

from classes.rules.rule_base_executor import RuleBaseExecutor
from classes.rules.rule_conditions import RuleAvailability, RuleComparison, RuleConditionGroupKey, RuleOperand, \
    RuleConditionKey
from models.rule_model import NodeConditionOptions, NodeConditionComparison
from models.ui_models import UiListItem
from repositories.camera_repository import CameraRepository
from repositories.device_repository import DeviceRepository
from repositories.sensor_repository import SensorRepository

operators = {
    '>': operator.gt,
    '<': operator.lt,
    '>=': operator.ge,
    '<=': operator.le,
    '==': operator.eq,
    '!=': operator.ne
}


class RuleConditionExecutor(RuleBaseExecutor):
    def execute(self):
        if isinstance(self.node.data.options, NodeConditionOptions):
            condition_result = False
            # Выполняем все блоки условий, они все должны вернуть True
            for condition in self.node.data.options.conditions:
                if condition.group == RuleConditionGroupKey.AVAILABILITY.value:
                    # УСТРОЙСТВО
                    if condition.key == RuleConditionKey.AVAILABILITY_DEVICE.value:
                        condition_result = self.availability_device(
                            operand=condition.operand,
                            state=condition.action.state,
                            items=condition.items
                        )
                    # КАМЕРА
                    if condition.key == RuleConditionKey.AVAILABILITY_CAMERA.value:
                        condition_result = self.availability_camera(
                            operand=condition.operand,
                            state=condition.action.state,
                            items=condition.items
                        )
                    # СЕНСОР
                    # @TODO это временная заглушка, гарантирующая, что при отключенном устройстве будет отключен и сенсор
                    if condition.key == RuleConditionKey.AVAILABILITY_CAMERA.value:
                        condition_result = self.availability_sensor(
                            operand=condition.operand,
                            state=condition.action.state,
                            items=condition.items
                        )

                elif condition.group == RuleConditionGroupKey.IS.value:
                    if condition.key == RuleConditionKey.IS_SENSOR_VALUE:
                        condition_result = self.comparison_sensor(
                            operand=condition.operand,
                            action=condition.action,
                            items=condition.items
                        )

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
            items: list[UiListItem]
    ):
        # Все устройства должны иметь такой же статус, что и state
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

    """
    Camera availability condition
    """

    @classmethod
    def availability_camera(
            cls,
            operand: str,
            state: RuleAvailability,
            items: list[UiListItem]
    ):
        # Все камеры должны иметь такой же статус, что и state
        if operand == RuleOperand.AND.value:
            success = False
            for item in items:
                camera = CameraRepository.get_camera(item.id)
                success = camera.online == (state == RuleAvailability.ONLINE.value)
                if not success:
                    return False
            return success
        # Одна из камер должна иметь статус, равный state
        elif operand == RuleOperand.OR.value:
            for item in items:
                camera = CameraRepository.get_camera(item.id)
                if camera.online == (state == RuleAvailability.ONLINE.value):
                    return True
            return False
        # Ни одна из камер не должно иметь статус state
        elif operand == RuleOperand.NOT.value:
            success = False
            for item in items:
                camera = CameraRepository.get_camera(item.id)
                success = camera.online != (state == RuleAvailability.ONLINE.value)
                if not success:
                    return False
            return success

    """
    Sensor availability condition
    """

    @classmethod
    def availability_sensor(
            cls,
            operand: str,
            state: RuleAvailability,
            items: list[UiListItem]
    ):
        # Все сенсоры должны иметь такой же статус, что и state
        if operand == RuleOperand.AND.value:
            success = False
            for item in items:
                sensor = SensorRepository.get_sensor(item.id)
                success = sensor.device.online == (state == RuleAvailability.ONLINE.value)
                if not success:
                    return False
            return success
        # Один из сенсоров должно иметь статус, равный state
        elif operand == RuleOperand.OR.value:
            for item in items:
                sensor = SensorRepository.get_sensor(item.id)
                if sensor.device.online == (state == RuleAvailability.ONLINE.value):
                    return True
            return False
        # Ни одно из сенсоров не должно иметь статус state
        elif operand == RuleOperand.NOT.value:
            success = False
            for item in items:
                sensor = SensorRepository.get_sensor(item.id)
                success = sensor.device.online != (state == RuleAvailability.ONLINE.value)
                if not success:
                    return False
            return success

    """
    Comparison sensor condition
    """

    @classmethod
    def comparison_sensor(
            cls,
            operand: str,
            action: NodeConditionComparison,
            items: list[UiListItem]
    ):

        if operand == RuleOperand.AND.value:
            for item in items:
                sensor = SensorRepository.get_sensor(item.id)
                if not operators[action.operator](float(sensor.value), float(action.value)):
                    return False
            return True

        elif operand == RuleOperand.OR.value:
            for item in items:
                sensor = SensorRepository.get_sensor(item.id)
                if operators[action.operator](float(sensor.value), float(action.value)):
                    return True
            return False

        elif operand == RuleOperand.NOT.value:
            for item in items:
                sensor = SensorRepository.get_sensor(item.id)
                if operators[action.operator](float(sensor.value), float(action.value)):
                    return False
            return True
        else:
            return False

    """
    Comparison storage condition
    """

    @classmethod
    def comparison_storage(cls):
        pass
