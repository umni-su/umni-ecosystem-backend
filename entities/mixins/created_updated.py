from datetime import datetime

from sqlalchemy import Column, DateTime
from sqlalchemy.orm import declared_attr, declarative_mixin


@declarative_mixin
class TimeStampMixin:
    @declared_attr
    def created_at(self):
        return Column(
            DateTime, nullable=False, default=datetime.now()
        )

    @declared_attr
    def updated(self):
        return Column(DateTime, onupdate=datetime.now(), default=datetime.now())
