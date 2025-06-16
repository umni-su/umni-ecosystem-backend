from sqlmodel import SQLModel, Field

from .mixins.created_updated import TimeStampMixin


class UserEntity(SQLModel, TimeStampMixin, table=True):
    __tablename__ = 'users'
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    password: str = Field(index=True)
    email: str = Field(unique=True)
    firstname: str = Field(nullable=True)
    lastname: str = Field(nullable=True)
