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
from typing import Optional, List, Any, Union

from pydantic import BaseModel, Field, field_validator, ConfigDict, AnyHttpUrl

from classes.rules.rule_conditions import RuleComparison, RuleAvailability
from models.ui_models import UiListItem


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
    ACTION_RECORD = 'action.record'
    ENTITIES_SENSOR = 'action.sensor'
    ACTION_ALARM_ON = 'action.alarm.on'
    ACTION_ALARM_OFF = 'action.alarm.off'
    ACTION_NOTIFICATION = 'action.notification'
    ACTION_EMAIL = 'action.email'
    ACTION_TELEGRAM = 'action.telegram'
    ACTION_WEBHOOK = 'action.webhook'
    ACTION_SCREENSHOT = 'action.camera.screenshot'
    ACTION_RECORD_START = 'action.record.start'
    ACTION_RECORD_END = 'action.record.start'


class NodeConditionActionAvailable(BaseModel):
    state: RuleAvailability = Field(default=RuleAvailability.ONLINE)

    class Config:
        json_encoders = {
            RuleAvailability: lambda v: v.value
        }
        use_enum_values = True  # Эта опция автоматически использует значения enum


class NodeConditionComparison(BaseModel):
    operator: RuleComparison = Field(default=RuleComparison.LESS_THAN)
    value: int | str | None = None

    class Config:
        json_encoders = {
            RuleComparison: lambda v: v.value
        }
        use_enum_values = True  # Эта опция автоматически использует значения enum


class RuleNodeConditionItem(BaseModel):
    operand: str
    group: str
    key: str
    items: Optional[List[UiListItem]]
    action: NodeConditionActionAvailable | NodeConditionComparison | None = None


class NodeTriggerOptions(BaseModel):
    ids: Optional[List[int]] = None
    items: list[UiListItem] | None = None


class NodeConditionOptions(BaseModel):
    conditions: Optional[List[RuleNodeConditionItem]] | None = None


class NodeActionWebhookOptions(BaseModel):
    url: str | None = None


class NodeActionNotificationOptions(BaseModel):
    notification_id: int
    to: [str] = Field(default_factory=list)
    subject: str | None = None
    message: str | None = None
    model_config = ConfigDict(arbitrary_types_allowed=True)


class NodeActionOptions(BaseModel):
    """
    Action universal model
    """
    action: NodeActionNotificationOptions | NodeActionWebhookOptions


# class NodeOptions(BaseModel):
#     ids: Optional[List[int]] = None
#     conditions: Optional[List[RuleNodeConditionItem]] | None = None


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
    options: Optional[NodeTriggerOptions | NodeConditionOptions | NodeActionOptions] | None = None
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


# class NodeDataOptions(BaseModel):
#     state: Optional[str] = None
#     action: Optional[str] = None


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
    options: Optional[NodeTriggerOptions | NodeConditionOptions | NodeActionOptions] | None = None
    flow: NodeDataFlow


class NodeCreate(BaseModel):
    id: str
    type: str
    position: NodePosition | None
    data: NodeData


class NodeDataWithList(NodeData):
    options: Optional[NodeTriggerOptions | NodeConditionOptions | NodeActionOptions] | None = None
    flow: NodeDataFlow


class NodeVisualize(NodeCreate):
    id: str
    rule_id: int | None = None
    type: str
    key: str | None = None
    position: NodePosition | None
    data: NodeDataWithList
    children: list["NodeVisualize"] = Field(default_factory=list)
    source: str | None = None


class EdgeStyle(BaseModel):
    stroke: Optional[str] = None
    strokeWidth: Optional[int] = 1


class EdgeCreate(BaseModel):
    id: str
    source: str
    target: str
    source_handle: Optional[str] = Field(None, alias="sourceHandle")
    target_handle: Optional[str] = Field(None, alias="targetHandle")
    animated: bool = Field(False)
    style: EdgeStyle = Field(default_factory=EdgeStyle)

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
