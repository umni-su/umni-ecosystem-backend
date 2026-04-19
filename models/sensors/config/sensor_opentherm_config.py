# Copyright (C) 2026 Mikhail Sazanov
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

from pydantic import BaseModel


class BoundItem(BaseModel):
    min: float
    max: float


class Bounds(BaseModel):
    ch: BoundItem
    dhw: BoundItem
    hcr: BoundItem


class BoilerConfig(BaseModel):
    control_type: str
    dhw_present: bool
    dhw_config: str
    ch2_present: bool
    cooling_supported: bool
    pump_control_allowed: bool
    slave_ot_version: int
    slave_product_version: int


class SupportedFeatures(BaseModel):
    modulation_read: bool
    modulation_write: bool
    heat_curve_read: bool
    heat_curve_write: bool
    outside_temperature: bool
    return_temperature: bool
    pressure: bool
    flow_rate: bool
    dhw_present: bool
    modulating: bool


class OpenthermConfig(BaseModel):
    en: bool
    ready: bool
    adapter_success: bool
    status_code: int
    ch_en: bool
    ch_sp: float
    dhw_en: bool
    dhw_sp: float
    otc_en: bool
    cool_en: bool
    ch2_en: bool
    mod: float
    hcr: float
    ch_active: bool
    dhw_active: bool
    flame_on: bool
    is_fault: bool
    boiler_temperature: float
    return_temperature: float
    dhw_temperature: float
    outside_temperature: float
    modulation: float
    pressure: float
    flow_rate: float
    flow_rate_ch2: float
    fault_code: int
    boiler_config: BoilerConfig
    bounds: Bounds
    supported_features: SupportedFeatures
