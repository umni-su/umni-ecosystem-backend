from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, JSON
from entities.mixins.created_updated import TimeStampMixin
from entities.mixins.id_column import IdColumnMixin


class RuleNodeBase(SQLModel):
    id: str = Field(
        index=True,
        primary_key=True
    )
    type: Optional[str] = Field(
        default=None,
        index=True,
        description=" -> RuleNodeTypes"
    )
    position: Optional[Dict[str, Any]] = Field(
        sa_type=JSON,
        default=None,
        nullable=True,
        description=" -> NodePosition"
    )
    rule_id: int = Field(
        index=True,
        foreign_key="rules.id"
    )
    data: Optional[Dict[str, Any]] = Field(
        sa_type=JSON,
        default=None,
        nullable=True,
        description=" -> RuleNodeData"
    )


class RuleNode(
    RuleNodeBase,
    table=True
):
    __tablename__ = "rule_nodes"

    key: Optional[str] = Field(
        default=None,
        description=" -> RuleNodeTypeKeys"
    )
    entity_id: Optional[int] = Field(
        index=True
    )
    entity_type: Optional[str] = Field(
        default=None,
        description=" -> RuleEntityType"
    )
    rule: "RuleEntity" = Relationship(
        sa_relationship_kwargs=dict(
            # lazy="selectin"
        ),
        back_populates="nodes"
    )


class RuleEdge(SQLModel, table=True):
    __tablename__ = "rule_edges"

    id: str = Field(
        index=True,
        primary_key=True
    )
    source: str = Field(
        index=True,
        foreign_key="rule_nodes.id"
    )
    target: str = Field(
        index=True,
        foreign_key="rule_nodes.id"
    )
    source_handle: Optional[str] = Field(
        default=None,
        index=True,
    )
    target_handle: Optional[str] = Field(
        default=None,
        index=True,
    )
    rule_id: int = Field(
        index=True,
        foreign_key="rules.id"
    )
    rule: "RuleEntity" = Relationship(
        sa_relationship_kwargs=dict(
            # lazy="selectin"
        ),
        back_populates="edges"
    )


class RuleEntityBase(SQLModel):
    name: str
    description: Optional[str] = None
    enabled: bool = Field(
        default=True,
        index=True
    )
    priority: int = Field(
        default=0
    )


class RuleEntity(TimeStampMixin, RuleEntityBase, IdColumnMixin, table=True):
    __tablename__ = "rules"

    nodes: List[RuleNode] = Relationship(
        sa_relationship_kwargs=dict(
            # lazy="selectin",
            cascade="all, delete-orphan"
        ),

    )
    edges: List[RuleEdge] = Relationship(
        sa_relationship_kwargs=dict(
            # lazy="selectin",
            cascade="all, delete-orphan"
        ),
    )
