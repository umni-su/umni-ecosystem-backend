"""recreate rulenodetypes enum

Revision ID: a38a58dce7c0
Revises: d22808b5f0bc
Create Date: 2025-08-19 16:53:35.036288

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a38a58dce7c0'
down_revision: Union[str, None] = 'd22808b5f0bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Сначала удаляем существующий тип
    op.execute('DROP TYPE IF EXISTS rulenodetypekeys CASCADE')

    # Создаем новый тип с обновленными значениями
    rulenodetypekeys = postgresql.ENUM(
        'RULE_START',
        'RULE_END',
        'RULE_CONDITION',
        'SENSORS_CHANGES',
        'DEVICES_CHANGES',
        'MOTION_START',
        'MOTION_END',
        'ACTION_ALARM_ON',
        'ACTION_ALARM_OFF',
        'ACTION_EMAIL',
        'ACTION_TELEGRAM',
        'ACTION_WEBHOOK',
        'ACTION_RECORD',
        'ACTION_SCREENSHOT',
        'ENTITIES_DEVICE',
        'ENTITIES_CAMERA',
        'ENTITIES_SENSOR',
        name='rulenodetypekeys'
    )
    rulenodetypekeys.create(op.get_bind())

    op.execute('DROP TYPE IF EXISTS rulenodetypes CASCADE')

    # Создаем новый тип с обновленными значениями
    rulenodetypes = postgresql.ENUM(
        'TRIGGER', 'CONDITION', 'ENTITY', 'CAMERA', 'DEVICE', 'ACTION', 'START', 'END',
        name='rulenodetypes'
    )
    rulenodetypes.create(op.get_bind())


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем новый тип
    op.execute('DROP TYPE IF EXISTS rulenodetypekeys CASCADE')
    op.execute('DROP TYPE IF EXISTS rulenodetypes CASCADE')
