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
import time
from datetime import datetime
from typing import Union, Optional, Any

from classes.devices.device_registry import device_registry
from classes.devices.device_sensor_type_enum import DeviceSensorTypeEnum
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from models.device_model_relations import DeviceModelWithRelations
from models.device_netif import DeviceNetifBase
from models.sensor_model import SensorModelWithDevice, SensorUpdateModel, SensorCreateModel
from plugins.core.umni_mdns.classes.device_rest_commands import DeviceRestCommands, SettingCapability
from plugins.core.umni_mdns.models.mdns_models import MDNSDevice
from repositories.device_repository import DeviceRepository
from repositories.sensor_repository import SensorRepository


class DeviceSynchronizer:
    def __init__(self, mdns_info: MDNSDevice, device: DeviceModelWithRelations):
        self.mdns_info = mdns_info
        self.device = device
        self.api = DeviceRestCommands(
            ip_address=mdns_info.ip,
            protocol=mdns_info.protocol
        )

    def sync_device(self):
        res = self.save_systeminfo()
        if res:
            self.save_sensors()

    def get_system_info(self):
        return self.api.get_system_info()

    def save_systeminfo(self) -> bool:
        try:
            system_info = self.get_system_info()
            systeminfo_data = system_info.data
            if system_info.success is True:
                device_registry.register_device(
                    plugin_id=self.device.plugin_id,
                    name=systeminfo_data.hostname,
                    external_id=systeminfo_data.hostname,
                    capabilities=systeminfo_data.capabilities,
                    free_heap=systeminfo_data.heap.free,
                    total_heap=systeminfo_data.heap.total
                )
                if systeminfo_data.networks:
                    for net in systeminfo_data.networks:
                        ni = DeviceNetifBase(
                            device_id=self.device.id,
                            name=net.name,
                            mac=net.mac,
                            ip=net.ip,
                            mask=net.mask,
                            gw=net.gw,
                            last_sync=datetime.now()
                        )
                        DeviceRepository.save_network_interface(ni)
                Logger.debug(
                    f'DeviceSynchronizer ({self.device.id}, {self.device.external_id}) finished register device',
                    LoggerType.PLUGINS)
                return True
            return False
        except Exception as e:
            Logger.err(
                f'DeviceSynchronizer ({self.device.id}, {self.device.external_id}) failed to register device: {e}',
                LoggerType.PLUGINS)
            return False

    def _update_or_create_sensor(
            self,
            identifier: str,
            name: str,
            capability: str,
            stype: DeviceSensorTypeEnum,
            active: bool = True,
            value: Union[str | float | int | bool | None] = None,
            options: dict[str, Any] = None
    ):
        try:
            sensor = SensorRepository.get_sensor_by_device_and_identifier(
                device_id=self.device.id,
                identifier=identifier,
            )
            # Update sensor
            if isinstance(sensor, SensorModelWithDevice):
                model = SensorUpdateModel.model_validate(
                    sensor.model_dump(exclude_none=True)
                )
                model.name = name
                model.capability = capability
                model.type = stype
                model.active = active
                model.last_sync = datetime.now()
                if value is not None:
                    model.value = value
                return SensorRepository.update_sensor(model)
            else:
                model = SensorCreateModel(
                    device_id=self.device.id,
                    type=stype.value,
                    capability=capability,
                    identifier=identifier,
                    active=active,
                    name=name,
                    last_sync=datetime.now(),
                    visible_name=name,
                    options=options,
                    photo=None,
                    unit=None,
                    icon=None
                )
                if value is not None:
                    model.value = str(value)
                return SensorRepository.create_sensor(model)
        except Exception as e:
            print(e)

    def save_sensors(self):
        caps = self.device.capabilities  # Список строк: ['ntc', 'onewire', ...]

        for setting in SettingCapability:
            # Проверяем строку в списке строк
            if setting in caps:

                # Сопоставляем строку со строкой
                match setting:
                    case SettingCapability.OUTPUTS:
                        res = self.api.get_outputs_info()
                        if not res.success:
                            return
                        for s in res.data.outputs:
                            identifier = f'out{s.index}'
                            self._update_or_create_sensor(
                                identifier=identifier,
                                name=s.label,
                                capability=SettingCapability.OUTPUTS.value,
                                stype=DeviceSensorTypeEnum.SWITCH,
                                active=s.active,
                                value=s.state
                            )

                        time.sleep(1)
                    case SettingCapability.INPUTS:
                        res = self.api.get_inputs_info()
                        if not res.success:
                            return
                        for s in res.data.inputs:
                            identifier = f'inp{s.index}'
                            self._update_or_create_sensor(
                                identifier=identifier,
                                name=s.label,
                                capability=SettingCapability.INPUTS.value,
                                stype=DeviceSensorTypeEnum.INPUT,
                                active=s.active,
                                value=s.state
                            )
                        time.sleep(1)
                    case SettingCapability.AI:
                        res = self.api.get_adc_info()
                        if not res.success:
                            return
                        for s in res.data.channels:
                            identifier = f'ai{(s.id + 1)}'  # case starts from 0
                            self._update_or_create_sensor(
                                identifier=identifier,
                                name=s.label,
                                capability=SettingCapability.AI.value,
                                stype=DeviceSensorTypeEnum.NUMBER,
                                active=s.active
                            )
                        time.sleep(1)
                    case SettingCapability.NTC:
                        res = self.api.get_ntc_info()
                        if not res.success:
                            return
                        for s in res.data.channels:
                            identifier = f'ntc{(s.id + 1)}'
                            self._update_or_create_sensor(
                                identifier=identifier,
                                name=s.label,
                                capability=SettingCapability.NTC.value,
                                stype=DeviceSensorTypeEnum.FLOAT,
                                active=s.active
                            )
                        time.sleep(1)
                    case SettingCapability.OPENCOLLECTORS:
                        res = self.api.get_opencollectors_info()
                        if not res.success:
                            return
                        for s in res.data.opencollectors:
                            identifier = f'oc{(s.index + 1)}'
                            self._update_or_create_sensor(
                                identifier=identifier,
                                name=s.label,
                                capability=SettingCapability.OPENCOLLECTORS.value,
                                stype=DeviceSensorTypeEnum.SWITCH,
                                active=s.active
                            )
                        time.sleep(1)
                    case SettingCapability.RF433:
                        res = self.api.get_rf433_info()
                        if not res.success:
                            return
                        for s in res.data.devices:
                            identifier = s.serial
                            self._update_or_create_sensor(
                                identifier=identifier,
                                name=s.label,
                                capability=SettingCapability.RF433.value,
                                stype=DeviceSensorTypeEnum.NUMBER,
                                active=s.alarm,
                                value=s.value,
                                options=s.model_dump()
                            )
                        time.sleep(1)
