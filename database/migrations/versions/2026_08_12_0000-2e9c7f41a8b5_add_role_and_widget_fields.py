"""Add sensor role and device widget_type/widget_name

Revision ID: 2e9c7f41a8b5
Revises: a2f771783568
Create Date: 2026-08-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2e9c7f41a8b5'
down_revision: Union[str, None] = 'a2f771783568'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Роль сенсора по типу (DeviceSensorTypeEnum.value -> роль).
# Дублируется с classes/devices/device_widget_service.py намеренно:
# миграция не должна импортировать код приложения.
TYPE_ROLE = {
    100: "power",        # SWITCH
    200: "setpoint",     # SETPOINT
    201: "temperature",  # TEMPERATURE
    202: "humidity",     # HUMIDITY
    203: "pressure",     # PRESSURE
    204: "battery",      # BATTERY
    205: "energy",       # ENERGY
    206: "power_meter",  # POWER (измерение, не управление)
    207: "voltage",      # VOLTAGE
    208: "current",      # CURRENT
    209: "co2",          # CO2
    210: "illuminance",  # ILLUMINANCE
    211: "motion",       # MOTION
    212: "contact",      # CONTACT
    213: "alarm",        # ALARM
    214: "lock",         # LOCK
    215: "fan",          # FAN
    300: "power",        # LIGHT
    301: "color",        # RGB
    302: "color",        # RGBA
    303: "color_temp",   # COLOR_TEMP
    304: "brightness",   # BRIGHTNESS
    305: "color",        # COLOR_HEX
}

# STRING (900) / INPUT (101) с перечислением значений - это режим
MODE_TYPES = {101, 900}


def _options_values(options) -> bool:
    if not isinstance(options, dict):
        return False
    values = options.get("values")
    return bool(values)


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('devices', sa.Column('widget_type', sa.String(), nullable=True))
    op.add_column('devices', sa.Column('widget_name', sa.String(), nullable=True))
    op.add_column('device_sensors', sa.Column('role', sa.String(), nullable=True))
    op.create_index('ix_device_sensors_role', 'device_sensors', ['role'])

    bind = op.get_bind()

    # Бэкафил ролей существующим сенсорам из типа сенсора
    rows = bind.execute(
        sa.text(
            "SELECT id, type, options FROM device_sensors WHERE role IS NULL"
        )
    ).fetchall()
    for sensor_id, sensor_type, options in rows:
        role = TYPE_ROLE.get(sensor_type)
        if role is None and sensor_type in MODE_TYPES and _options_values(options):
            role = "mode"
        if role:
            bind.execute(
                sa.text("UPDATE device_sensors SET role = :role WHERE id = :id"),
                {"role": role, "id": sensor_id},
            )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_device_sensors_role', table_name='device_sensors')
    op.drop_column('device_sensors', 'role')
    op.drop_column('devices', 'widget_name')
    op.drop_column('devices', 'widget_type')
