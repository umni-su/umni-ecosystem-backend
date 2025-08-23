from typing import Optional, List, Dict, Any

from sqlmodel import SQLModel, Field, Relationship, JSON

from entities.mixins.created_updated import TimeStampMixin
from models.rule_model import RuleNodeTypes, RuleNodeTypeKeys, RuleEntityType, NodePosition, RuleNodeData
from entities.mixins.id_column import IdColumnMixin


class RuleNodeBase(SQLModel):
    id: str = Field(primary_key=True)
    type: Optional[str] = None
    position: Optional[Dict[str, Any]] = Field(sa_type=JSON, default=None, nullable=True)
    rule_id: int = Field(foreign_key="rules.id")
    data: Optional[Dict[str, Any]] = Field(sa_type=JSON, default=None, nullable=True)


class RuleNode(RuleNodeBase, table=True):
    __tablename__ = "rule_nodes"
    key: Optional[RuleNodeTypeKeys] = None
    entity_id: Optional[int] = None
    entity_type: Optional[RuleEntityType] = None
    rule: "RuleEntity" = Relationship(
        sa_relationship_kwargs=dict(lazy="subquery"),
        back_populates="nodes")


class RuleEdge(SQLModel, table=True):
    __tablename__ = "rule_edges"
    id: str = Field(primary_key=True)
    source: str = Field(foreign_key="rule_nodes.id")
    target: str = Field(foreign_key="rule_nodes.id")
    source_handle: Optional[str] = None
    target_handle: Optional[str] = None
    rule_id: int = Field(foreign_key="rules.id")
    rule: "RuleEntity" = Relationship(
        sa_relationship_kwargs=dict(lazy="subquery"),
        back_populates="edges")


class RuleEntityBase(SQLModel):
    name: str
    description: Optional[str] = None
    enabled: bool = Field(default=True)
    priority: int = Field(default=0)


class RuleEntity(TimeStampMixin, RuleEntityBase, IdColumnMixin, table=True):
    __tablename__ = "rules"
    nodes: List[RuleNode] = Relationship(
        sa_relationship_kwargs=dict(
            lazy="subquery",
            cascade="all, delete-orphan"
        ),

    )
    edges: List[RuleEdge] = Relationship(
        sa_relationship_kwargs=dict(
            lazy="subquery",
            cascade="all, delete-orphan"
        ),
    )
