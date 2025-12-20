from typing import Optional, Dict, Any
from datetime import datetime
from sqlmodel import Field, JSON, Column, DateTime

from entities.mixins.created_updated import TimeStampMixin
from entities.mixins.id_column import IdColumnMixin


class LogEntryBase:
    entity_id: int = Field(
        nullable=True,
        index=True
    )

    code: int = Field(
        nullable=True,
        index=True
    )

    timestamp: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True),
        default_factory=datetime.now
    )

    level: str = Field(
        nullable=False,
        index=True
    )
    logger_type: str = Field(
        nullable=False,
        index=True
    )
    message: str = Field(
        nullable=False,
        max_length=10000
    )

    details: Optional[Dict[str, Any]] = Field(
        sa_column=Column(JSON),
        default=None
    )


class LogEntity(TimeStampMixin, LogEntryBase, IdColumnMixin, table=True):
    __tablename__ = 'logs'
