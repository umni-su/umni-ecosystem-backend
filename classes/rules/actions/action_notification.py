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
from classes.rules.rule_base_executor import RuleBaseExecutor
from models.notification_queue_model import NotificationQueueCreateModel
from models.rule_model import NodeActionOptions, RuleModel
from repositories.notification_queue_repository import NotificationQueueRepository
from repositories.rules_repository import RulesRepository


class ActionNotificationExecutor(RuleBaseExecutor):
    subject: str = ''

    message: str = ''

    def execute(self):
        options = self.node.data.options
        if isinstance(options, NodeActionOptions):
            if isinstance(options.action.to, list):
                for to in options.action.to:
                    try:
                        rule = RulesRepository.get_rule(self.node.rule_id)
                        if rule:
                            n = NotificationQueueCreateModel(
                                notification_id=options.action.notification_id,
                                to=to,
                                subject=self._modify_subject(rule, options),
                                message=options.action.message
                            )
                            NotificationQueueRepository.create_queue_item(n)
                    except Exception as e:
                        Logger.err(f"Failed to create notification queue item: {e}", LoggerType.RULES)

    def _modify_subject(self, rule: RuleModel, options: NodeActionOptions):
        return f'[RULE: {rule.name}]\r\n{options.action.subject}'
