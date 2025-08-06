from enum import StrEnum

from pydantic import BaseModel

"""
Rule Node types
"""


class RuleNodeTypes(StrEnum):
    TRIGGER = 'trigger'
    CONDITION = 'condition'
    ENTITIY = 'entity'
    ACTION = 'action'


class RuleNodeTypeKeys(StrEnum):
    RULE_START = 'rule.start'
    RULE_END = 'rule.end'
    SENSORS_CHANGES = 'sensors.change.state'
    DEVICES_CHANGES = 'devices.changes.state'
    MOTION_START = 'camera.motion.start'
    MOTION_END = 'camera.motion.end'
    ALARM_ON = 'action.alarm.on'
    ALARM_OFF = 'action.alarm.off'
    ACTION_EMAIL = 'action.email'
    ACTION_TELEGRAM = 'action.telegram'
    ACTION_WEBHOOK = 'action.webhook'


class RuleModel(BaseModel):
    type: RuleNodeTypes
    keys: list[RuleNodeTypeKeys]


# { "operand": "or", "items": [], "flow": { "el": { "type": "condition", "title": "Состояние", "icon": "mdi-circle-outline", "key": "rule.condition" }, "index": 2, "group": "conditions" } }
# { "flow": { "el": { "type": "trigger", "title": "Данные сенсора", "icon": "mdi-database-import", "key": "sensors.changes.state" }, "index": 0, "group": "triggers" } }
class RuleKeyData(BaseModel):
    pass


rule_trigger = RuleModel(
    type=RuleNodeTypes.TRIGGER,
    keys=[
        RuleNodeTypeKeys.DEVICES_CHANGES,
        RuleNodeTypeKeys.SENSORS_CHANGES,
        RuleNodeTypeKeys.MOTION_START,
        RuleNodeTypeKeys.MOTION_END,
    ]
)

rule_action = RuleModel(
    type=RuleNodeTypes.ACTION,
    keys=[
        RuleNodeTypeKeys.ALARM_ON,
        RuleNodeTypeKeys.ALARM_OFF,
        RuleNodeTypeKeys.ACTION_EMAIL,
        RuleNodeTypeKeys.ACTION_TELEGRAM,
        RuleNodeTypeKeys.ACTION_WEBHOOK,
    ]
)
