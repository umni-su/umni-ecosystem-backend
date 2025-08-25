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


class RuleNodeListItem(BaseModel):
    id: int
    name: Optional[str] | None = None
    description: Optional[str] | None = None
    icon: Optional[str] | None = None
    color: Optional[str] | None = None


class RuleNodeEl(BaseModel):
    type: RuleNodeTypes | None = None
    icon: str | None = None
    key: RuleNodeTypeKeys | None = None
    title: str | None = None


class RuleNodeFlow(BaseModel):
    el: RuleNodeEl
    index: int | None = None
    group: str | None = None


class RuleNodeData(BaseModel):
    options: dict
    flow: RuleNodeFlow


class RuleNodePosition(BaseModel):
    x: float
    y: float


class RuleNodeModel(BaseModel):
    id: str
    type: Optional[RuleNodeTypes] = None
    position: RuleNodePosition | None = None
    rule_id: int
    data: RuleNodeData | None = None

    @classmethod
    @field_validator('position', mode='before')
    def validate_position(cls, v):
        if isinstance(v, dict):
            return NodePosition(**v)
        return v

    @classmethod
    @field_validator('data', mode='before')
    def validate_data(cls, v):
        if isinstance(v, dict):
            return RuleNodeData(**v)
        return v


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
    options: Optional[Dict] = Field(default_factory=dict)
    flow: NodeDataFlow


class NodeCreate(BaseModel):
    id: str
    type: str
    position: NodePosition | None
    data: NodeData


class NodeDataWithList(NodeData):
    options: Optional[Dict] = Field(default_factory=dict)
    flow: NodeDataFlow
    items: List[RuleNodeListItem] = Field(default_factory=list)


class NodeVisualize(NodeCreate):
    id: str
    type: str
    position: NodePosition | None
    data: NodeDataWithList


class EdgeCreate(BaseModel):
    id: str
    source: str
    target: str
    source_handle: Optional[str] = Field(None, alias="sourceHandle")
    target_handle: Optional[str] = Field(None, alias="targetHandle")

    class Config:
        populate_by_name = True


class RuleGraphUpdate(BaseModel):
    nodes: List[NodeVisualize] = Field(default=list[NodeVisualize])
    edges: List[EdgeCreate] = Field(default=list[EdgeCreate])


class RuleModel(RuleGraphUpdate, RuleCreate):
    id: int | None = Field(default=None)

    @classmethod
    @field_validator('nodes', mode='before')
    def validate_nodes(cls, v):
        if v is None:
            return []
        return [RuleNodeModel(**node) if isinstance(node, dict) else node for node in v]


class RuleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    enabled: Optional[bool] = None

# { "operand": "or", "items": [], "flow": { "el": { "type": "condition", "title": "Состояние", "icon": "mdi-circle-outline", "key": "rule.condition" }, "index": 2, "group": "conditions" } }
# { "flow": { "el": { "type": "trigger", "title": "Данные сенсора", "icon": "mdi-database-import", "key": "sensors.changes.state" }, "index": 0, "group": "triggers" } }
