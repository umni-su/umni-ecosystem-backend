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

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class MDNSDeviceBase(BaseModel):
    """Базовая модель устройства mDNS"""
    unique_id: str = Field(..., description="Device unique ID")
    name: str = Field(..., description="Device name")
    ip: str = Field(..., description="Device ip")
    port: int = Field(..., description="Device port")
    service_type: str = Field(..., description="mDNS service type")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Additional properties")


class MDNSDevice(BaseModel):
    """Модель устройства mDNS"""
    unique_id: str = Field(..., description="Уникальный ID")
    name: str = Field(..., description="Имя устройства")
    ip: str = Field(..., description="IP адрес")
    port: int = Field(..., description="Порт")
    service_type: str = Field(..., description="Тип сервиса")
    service_name: str = Field(..., description="Полное имя сервиса")
    server: Optional[str] = Field(None, description="Имя сервера")
    properties: Dict[str, Any] = Field(default_factory=dict)
    first_seen: datetime = Field(default_factory=datetime.now)
    last_seen: datetime = Field(default_factory=datetime.now)

    def is_online(self, timeout_seconds: int = 60) -> bool:
        """Проверяет, онлайн ли устройство"""
        return (datetime.now() - self.last_seen).total_seconds() < timeout_seconds

    def update_timestamp(self):
        """Обновляет время последнего обнаружения"""
        self.last_seen = datetime.now()


class MDNSScanResult(BaseModel):
    """Результат сканирования"""
    devices: List[MDNSDevice] = Field(default_factory=list)
    total_count: int = 0
    scan_started: datetime = Field(default_factory=datetime.now)
    scan_finished: Optional[datetime] = None
    errors: List[str] = Field(default_factory=list)

    def add_device(self, device: MDNSDevice):
        """Добавляет или обновляет устройство"""
        for i, existing in enumerate(self.devices):
            if existing.unique_id == device.unique_id:
                device.first_seen = existing.first_seen
                self.devices[i] = device
                return
        self.devices.append(device)
        self.total_count = len(self.devices)

    def remove_device(self, unique_id: str) -> bool:
        """Удаляет устройство по ID"""
        original_count = len(self.devices)
        self.devices = [d for d in self.devices if d.unique_id != unique_id]
        self.total_count = len(self.devices)
        return len(self.devices) < original_count

    def get_device(self, unique_id: str) -> Optional[MDNSDevice]:
        """Получает устройство по ID"""
        for device in self.devices:
            if device.unique_id == unique_id:
                return device
        return None

    def get_devices_by_ip(self, ip: str) -> List[MDNSDevice]:
        """Получает устройства по IP"""
        return [d for d in self.devices if d.ip == ip]
