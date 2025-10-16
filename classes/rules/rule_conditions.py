# Copyright (C) 2025 Mikhail Sazanov
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from enum import StrEnum, Enum
from classes.l10n.l10n import _
from pydantic import BaseModel


class RuleAvailability(Enum):
    OFFLINE = 0
    ONLINE = 1
    UNKNOWN = 2


class RuleComparison(StrEnum):
    LESS_THAN = "<"
    GREATER_THAN = ">"
    LESS_THAN_OR_EQUAL = "<="
    GREATER_THAN_OR_EQUAL = ">="
    EQUAL = "="
    NOT_EQUAL = "!="


class RuleConditionGroupKey(StrEnum):
    AVAILABILITY = 'availability'
    IS = 'is'
    STATE = 'state'


class RuleConditionKey(StrEnum):
    # availability group = online 1 | offline 0
    AVAILABILITY_DEVICE = 'availability.device'
    AVAILABILITY_CAMERA = 'availability.camera'
    AVAILABILITY_SENSOR = 'availability.sensor'
    # is group = < > <= >= == !=
    IS_STORAGE_SIZE = 'is.storage.size'
    IS_SENSOR_VALUE = 'is.sensor.value'
    # state group = any busy, not busy
    STATE_CAMERA_RECORDING = 'state.camera.recording'


class RuleCondition(BaseModel):
    key: RuleConditionKey
    label: str
    icon: str


class RuleConditionGroup(BaseModel):
    key: RuleConditionGroupKey
    label: str
    icon: str | None = None
    items: list[RuleCondition]


class RuleConditionsList:
    conditions: list[RuleConditionGroup]

    def __init__(self):
        self.conditions = [
            RuleConditionGroup(
                key=RuleConditionGroupKey.AVAILABILITY,
                label=_('Availability'),
                icon='mdi-heart-multiple',
                items=[
                    RuleCondition(
                        key=RuleConditionKey.AVAILABILITY_DEVICE,
                        label=_('Device availability'),
                        icon='mdi-robot'
                    ),
                    RuleCondition(
                        key=RuleConditionKey.AVAILABILITY_CAMERA,
                        label=_('Camera availability'),
                        icon='mdi-camera'
                    ),
                    RuleCondition(
                        key=RuleConditionKey.AVAILABILITY_SENSOR,
                        label=_('Sensor availability'),
                        icon='mdi-thermometer'
                    )
                ]
            ),
            RuleConditionGroup(
                key=RuleConditionGroupKey.IS,
                label=_('Comparison'),
                icon='mdi-not-equal-variant',
                items=[
                    RuleCondition(
                        key=RuleConditionKey.IS_STORAGE_SIZE,
                        label=_('Storage size'),
                        icon='mdi-harddisk'
                    ),
                    RuleCondition(
                        key=RuleConditionKey.IS_SENSOR_VALUE,
                        label=_('Sensor value'),
                        icon='mdi-thermometer-check'
                    )
                ]
            ),
            RuleConditionGroup(
                key=RuleConditionGroupKey.STATE,
                label=_('State'),
                icon='mdi-list-status',
                items=[
                    RuleCondition(
                        key=RuleConditionKey.STATE_CAMERA_RECORDING,
                        label=_('Recording state'),
                        icon='mdi-record-rec'
                    )
                ]
            )
        ]
