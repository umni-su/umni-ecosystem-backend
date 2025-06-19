from sqlmodel import SQLModel, Field

from .mixins.created_updated import TimeStampMixin
from entities.mixins.id_column import IdColumnMixin


class UserEntityBase:
    username: str = Field(index=True, unique=True)
    password: str = Field(index=True)
    email: str = Field(unique=True)
    firstname: str = Field(nullable=True)
    lastname: str = Field(nullable=True)


class UserEntity(TimeStampMixin, UserEntityBase, IdColumnMixin, table=True):
    __tablename__ = 'users'
