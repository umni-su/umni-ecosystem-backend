from enum import StrEnum
from typing import Dict, Any, Optional, List

from pydantic import BaseModel, Field, field_validator, computed_field

"""
Rule Node types
"""


class RuleEntityType(StrEnum):
    DEVICE = 'device'
    SENSOR = 'sensor'
    CAMERA = 'camera'


class RuleNodeTypes(StrEnum):
    TRIGGER = 'trigger'
    CONDITION = 'condition'
    ENTITY = 'entity'
    DEVICE = 'device'
    CAMERA = 'camera'
    ACTION = 'action'
    START = 'start'
    END = 'end'


class RuleNodeTypeKeys(StrEnum):
    RULE_START = 'rule.start'
    RULE_END = 'rule.end'
    RULE_CONDITION = 'rule.condition'
    # TRIGGERS
    SENSORS_CHANGES = 'sensors.changes.state'
    DEVICES_CHANGES = 'devices.changes.state'
    MOTION_START = 'camera.motion.start'
    MOTION_END = 'camera.motion.end'
    # ACTIONS
    ACTION_CAMERA = 'action.camera'
    ACTION_DEVICE = 'action.device'
    ENTITIES_SENSOR = 'action.sensor'
    ACTION_ALARM_ON = 'action.alarm.on'
    ACTION_ALARM_OFF = 'action.alarm.off'
    ACTION_EMAIL = 'action.email'
    ACTION_TELEGRAM = 'action.telegram'
    ACTION_WEBHOOK = 'action.webhook'
    ACTION_SCREENSHOT = 'action.camera.screenshot'
    ACTION_RECORD_START = 'action.record.start'
    ACTION_RECORD_END = 'action.record.start'


class RuleNodeData(BaseModel):
    options: dict
    flow: dict


class RuleNodePosition(BaseModel):
    x: float
    y: float


# Модели для создания/обновления правил
class RuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    enabled: Optional[bool] = Field(True)
    priority: Optional[int] = Field(default=None, ge=0)

    @classmethod
    @field_validator('priority')
    def set_default_priority(cls, v):
        return v if v is not None else 0


# Модели для работы с графом
class NodePosition(BaseModel):
    x: float
    y: float


class NodeDataOptions(BaseModel):
    entity_id: Optional[int] = None
    state: Optional[str] = None
    action: Optional[str] = None
    operand: Optional[str] = None  # Для условий
    items: Optional[List[Dict]] = None  # Для условий


class NodeDataFlowEl(BaseModel):
    type: str
    icon: Optional[str] = None
    key: Optional[str] = None
    title: Optional[str] = None


class NodeDataFlow(BaseModel):
    el: NodeDataFlowEl
    index: Optional[int] = None
    group: Optional[str] = None


class NodeData(BaseModel):
    options: Optional[NodeDataOptions] = Field(default_factory=dict)
    flow: NodeDataFlow


class NodeCreate(BaseModel):
    id: str
    type: str
    position: NodePosition | None
    data: NodeData


class EdgeCreate(BaseModel):
    id: str
    source: str
    target: str
    source_handle: Optional[str] = Field(None, alias="sourceHandle")
    target_handle: Optional[str] = Field(None, alias="targetHandle")

    class Config:
        populate_by_name = True


class RuleGraphUpdate(BaseModel):
    nodes: List[NodeCreate] = Field(default=list[NodeCreate])
    edges: List[EdgeCreate] = Field(default=list[EdgeCreate])


class RuleModel(RuleGraphUpdate, RuleCreate):
    id: int | None = Field(default=None)


class RuleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    enabled: Optional[bool] = None

# { "operand": "or", "items": [], "flow": { "el": { "type": "condition", "title": "Состояние", "icon": "mdi-circle-outline", "key": "rule.condition" }, "index": 2, "group": "conditions" } }
# { "flow": { "el": { "type": "trigger", "title": "Данные сенсора", "icon": "mdi-database-import", "key": "sensors.changes.state" }, "index": 0, "group": "triggers" } }
