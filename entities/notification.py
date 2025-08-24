from typing import Optional, Dict, Any

from sqlmodel import Field, Column, Boolean
from sqlalchemy.types import JSON
from sqlalchemy.sql import true

from entities.mixins.created_updated import TimeStampMixin
from entities.mixins.id_column import IdColumnMixin


class NotificationEntityBase:
    name: str = Field(
        nullable=False
    )
    to: str = Field(
        index=True,
        nullable=False
    )
    type: Optional[int] = Field(
        index=True,
        nullable=False,
        description=" -> NotificationTypeEnum"
    )
    active: bool = Field(
        sa_column=Column(
            Boolean,
            index=True,
            nullable=False,
            server_default=true()
        )
    )
    options: Optional[Dict[str, Any]] = Field(
        sa_type=JSON,
        default=None,
        nullable=True,
        description=" -> NotificationOptionsBaseModel"
    )


class NotificationEntity(
    TimeStampMixin,
    NotificationEntityBase,
    IdColumnMixin,
    table=True
):
    __tablename__ = 'notifications'
