from datetime import datetime
from sqlmodel import Field
from sqlalchemy import func


class TimeStampMixin:
    created: datetime = Field(default_factory=datetime.now, nullable=False)

    updated: datetime | None = Field(default_factory=datetime.now, nullable=False)

    # @declared_attr
    # def created(self):
    #     return Column(
    #         DateTime, nullable=False, default=datetime.now
    #     )
    #
    # @declared_attr
    # def updated(self):
    #     return Column(
    #         DateTime, onupdate=datetime.now, default=datetime.now
    #     )
