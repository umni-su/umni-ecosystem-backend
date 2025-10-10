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

from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, JSON

from entities.mixins.base_model_mixin import BaseModelMixin
from entities.mixins.created_updated import TimeStampMixin
from entities.mixins.id_column import IdColumnMixin


class RuleNodeBase(SQLModel, BaseModelMixin):
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
