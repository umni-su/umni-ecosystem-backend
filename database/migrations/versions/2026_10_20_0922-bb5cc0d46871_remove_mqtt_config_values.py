"""Remove mqtt.* config values

Revision ID: bb5cc0d46871
Revises: c6cccb1fd411
Create Date: 2026-10-20 09:22:42.473691

"""
from typing import Sequence, Union

import sqlmodel
from sqlmodel import col, delete

from database.session import write_session
from entities.configuration import ConfigurationEntity

# revision identifiers, used by Alembic.
revision: str = 'bb5cc0d46871'
down_revision: Union[str, None] = 'c6cccb1fd411'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with write_session() as session:
        query = delete(ConfigurationEntity).where(col(ConfigurationEntity.key).ilike("mqtt.%"))
        session.exec(query)


def downgrade() -> None:
    """Downgrade schema."""
    pass
