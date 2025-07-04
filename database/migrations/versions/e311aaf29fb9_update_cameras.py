"""Update cameras

Revision ID: e311aaf29fb9
Revises: 9ac5efe61713
Create Date: 2025-06-26 19:12:16.291082

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


import sqlmodel
# revision identifiers, used by Alembic.
revision: str = 'e311aaf29fb9'
down_revision: Union[str, None] = '9ac5efe61713'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('cameras', sa.Column('record_mode', sa.Enum('VIDEO', 'SCREENSHOTS', 'DETECTION_VIDEO', 'DETECTION_SCREENSHOTS', name='camerarecordtypeenum'), nullable=True))
    op.add_column('cameras', sa.Column('fps', sa.Integer(), nullable=True))
    op.add_column('cameras', sa.Column('scale', sa.Float(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('cameras', 'scale')
    op.drop_column('cameras', 'fps')
    op.drop_column('cameras', 'record_mode')
    # ### end Alembic commands ###
