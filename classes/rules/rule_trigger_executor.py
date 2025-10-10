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
from models.rule_model import RuleNodeTypeKeys


class RuleTriggerExecutor(RuleBaseExecutor):

    def execute(self):
        #
        # SENSORS_CHANGES = 'sensors.changes.state'
        # DEVICES_CHANGES = 'devices.changes.state'
        # MOTION_START = 'camera.motion.start'
        # MOTION_END = 'camera.motion.end'
        #
        if self.key == RuleNodeTypeKeys.SENSORS_CHANGES.value:
            print('exec SENSORS_CHANGES')
        elif self.key == RuleNodeTypeKeys.DEVICES_CHANGES.value:
            print('exec DEVICES_CHANGES')
        elif self.key == RuleNodeTypeKeys.MOTION_START:
            print('exec MOTION_START')
        elif self.key == RuleNodeTypeKeys.MOTION_END:
            print('exec MOTION_END')
