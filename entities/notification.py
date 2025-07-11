from typing import Optional

from sqlmodel import Field, Column, Boolean
from sqlalchemy.types import JSON
from sqlalchemy.sql import true

from entities.enums.notification_type_enum import NotificationTypeEnum
from entities.mixins.created_updated import TimeStampMixin
from entities.mixins.id_column import IdColumnMixin
from models.notification_model import NotificationOptionsBaseModel


class NotificationEntityBase:
    name: str = Field(nullable=False)
    to: str = Field(nullable=False)
    type: NotificationTypeEnum = Field(nullable=False)
    active: bool = Field(sa_column=Column(Boolean, nullable=False, server_default=true()))
    options: Optional[NotificationOptionsBaseModel | None] = Field(sa_column=Column(JSON, nullable=True))


class NotificationEntity(TimeStampMixin, NotificationEntityBase, IdColumnMixin, table=True):
    __tablename__ = 'notifications'
