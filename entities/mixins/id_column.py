from sqlmodel import Field
from sqlmodel import SQLModel

from entities.mixins.base_model_mixin import BaseModelMixin


class IdColumnMixin(SQLModel, BaseModelMixin,
                    ):
    id: int | None = Field(default=None, primary_key=True)
