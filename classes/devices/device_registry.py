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
import threading
from datetime import datetime, time
from time import sleep
from typing import Any, Optional, List, Dict

from sqlmodel import Session

from classes.devices.device_source_enum import DeviceSource, DeviceFeature
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from database.session import write_session
from entities.device import DeviceEntity
from entities.device_network_interfaces import DeviceNetworkInterface
from entities.sensor_entity import SensorEntity
from repositories.sensor_repository import SensorRepository
from services.mqtt.models.mqtt_register_model import MqttRegisterModel


class DeviceIPStore:
    """Простое хранилище IP адресов в памяти"""

    def __init__(self, ttl_seconds: int = 300):  # 5 минут по умолчанию
        self._ips: Dict[int, List[str]] = {}
        self._timestamps: Dict[int, datetime] = {}
        self._ttl = ttl_seconds
        self._lock = threading.Lock()

    def set_ip(self, device_id: int, ip: str):
        """Запомнить IP устройства"""
        with self._lock:
            if device_id not in self._ips:
                self._ips[device_id] = []

            if ip in self._ips[device_id]:
                self._ips[device_id].remove(ip)
            self._ips[device_id].insert(0, ip)
            self._ips[device_id] = self._ips[device_id][:3]

            self._timestamps[device_id] = datetime.now()

    def get_ip(self, device_id: int) -> Optional[str]:
        """Получить IP, если он не устарел"""
        with self._lock:
            if device_id not in self._timestamps:
                return None

            # Проверяем возраст
            age = (datetime.now() - self._timestamps[device_id]).total_seconds()
            if age > self._ttl:
                # Устарел - удаляем
                del self._ips[device_id]
                del self._timestamps[device_id]
                return None

            ips = self._ips.get(device_id, [])
            return ips[0] if ips else None

    def get_all_ips(self, device_id: int) -> List[str]:
        """
        Получить все IP для устройства, если не устарели
        Если устарели - возвращает пустой список и очищает запись
        """
        with self._lock:
            if device_id not in self._timestamps:
                return []

            # Проверяем возраст
            age = (datetime.now() - self._timestamps[device_id]).total_seconds()
            if age > self._ttl:
                # Устарел - удаляем всё
                if device_id in self._ips:
                    del self._ips[device_id]
                del self._timestamps[device_id]
                return []

            return self._ips.get(device_id, []).copy()

    def remove_device(self, device_id: int):
        """Удалить устройство"""
        with self._lock:
            if device_id in self._ips:
                del self._ips[device_id]
            if device_id in self._timestamps:
                del self._timestamps[device_id]

    def remove_ip(self, device_id: int, ip: str):
        """
        Удалить конкретный IP для устройства

        :param device_id: ID устройства
        :param ip: IP адрес для удаления
        """
        with self._lock:
            if device_id in self._ips:
                if ip in self._ips[device_id]:
                    self._ips[device_id].remove(ip)

                    # Если IP больше нет, удаляем устройство полностью
                    if not self._ips[device_id]:
                        del self._ips[device_id]
                        if device_id in self._timestamps:
                            del self._timestamps[device_id]

    def cleanup(self):
        """Очистить все устаревшие записи"""
        with self._lock:
            now = datetime.now()
            old_ids = [
                device_id
                for device_id, ts in self._timestamps.items()
                if (now - ts).total_seconds() > self._ttl
            ]

            for device_id in old_ids:
                del self._ips[device_id]
                del self._timestamps[device_id]


class DeviceRegistry:
    def __init__(self, ip_ttl_seconds: int = 5):  # 5 минут TTL
        self.ip_store = DeviceIPStore(ttl_seconds=ip_ttl_seconds)
        self._cleanup_thread = None
        self._start_cleanup()

    def _start_cleanup(self):
        """Фоновая очистка устаревших IP"""

        def cleanup_loop():
            while True:
                sleep(60)  # Каждую минуту
                self.ip_store.cleanup()

        self._cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        Logger.info('Device Registry cleanup thread started', LoggerType.DEVICES)

    def register_local_mqtt_device(
            self,
            new_or_existing_device: DeviceEntity,
            model: MqttRegisterModel,
            session: Session
    ):
        try:
            new_or_existing_device.name = model.hostname
            new_or_existing_device.type = model.device_type
            new_or_existing_device.fw_ver = model.fw_ver
            new_or_existing_device.free_heap = model.heap.free
            new_or_existing_device.total_heap = model.heap.total
            new_or_existing_device.uptime = model.uptime
            new_or_existing_device.capabilities = model.capabilities
            new_or_existing_device.last_sync = datetime.now()
            new_or_existing_device.online = True
            new_or_existing_device.source = DeviceSource.CORE.value
            new_or_existing_device.feature = DeviceFeature.MQTT.value
            session.add(new_or_existing_device)
            session.commit()
            session.refresh(new_or_existing_device)

            # Find network interfaces
            for netif in model.networks:
                ni = DeviceNetworkInterface()
                for device_netif in new_or_existing_device.network_interfaces:
                    if device_netif.mac == netif.mac:
                        ni = device_netif
                        break
                ni.mac = netif.mac
                ni.name = netif.name
                ni.ip = netif.ip
                ni.mask = netif.mask
                ni.gw = netif.gw
                ni.device = new_or_existing_device
                ni.last_sync = datetime.now()
                session.add(ni)

                # Сохраняем IP в кэш
                if netif.ip and netif.ip != "0.0.0.0":
                    self.ip_store.set_ip(new_or_existing_device.id, netif.ip)

            session.commit()
        except Exception as e:
            Logger.err(f'DeviceRegistry->register_local_mqtt_device() {str(e)}', LoggerType.DEVICES)

    def update_device_ip_from_db(self, device_id: int) -> Optional[str]:
        """Обновить IP из базы данных"""
        with write_session() as session:
            interfaces = session.query(DeviceNetworkInterface).filter_by(
                device_id=device_id
            ).all()

            for iface in interfaces:
                if iface.ip and iface.ip != "0.0.0.0":
                    self.ip_store.set_ip(device_id, iface.ip)
                    return iface.ip

        return None

    def get_device_ip(self, device_id: int, force_db: bool = False) -> Optional[str]:
        """
        Получить IP устройства

        :param device_id: ID устройства
        :param force_db: Принудительно загрузить из БД
        :return: IP адрес или None
        """
        # Если не нужно принудительно из БД
        if not force_db:
            ip = self.ip_store.get_ip(device_id)
            if ip:
                return ip

        # Иначе идем в БД
        return self.update_device_ip_from_db(device_id)

    def get_device_ips(self, device_id: int) -> List[str]:
        """
        Получить все известные IP для устройства

        Сначала пробует из кэша, если пусто - идет в БД
        """
        ips = self.ip_store.get_all_ips(device_id)
        if ips:
            return ips

        # Если в кэше пусто, пробуем загрузить из БД
        ip = self.update_device_ip_from_db(device_id)
        if ip:
            return [ip]
        return []

    def remove_device_ip(self, device_id: int, ip: str):
        """
        Удалить IP из кэша (например, если он перестал отвечать)

        :param device_id: ID устройства
        :param ip: IP адрес для удаления
        """
        self.ip_store.remove_ip(device_id, ip)

    def register_local_http_device(self):
        pass

    def register_device(
            self,
            feature: str,  # "http", "core"
            source: str,  # "core", "tuya", "tasmota", "mqtt" ...etc
            external_id: str,  # Уникальный ID в исходной системе
            name: str,
            device_type: str = "generic",
            **kwargs
    ) -> DeviceEntity:
        """Найти или создать устройство"""
        with write_session() as session:
            device = session.query(DeviceEntity).filter_by(
                source=source, external_id=external_id
            ).first()

            if not device:
                device = DeviceEntity(
                    feature=feature,
                    source=source,
                    external_id=external_id,
                    name=name,
                    type=device_type,
                    online=True,
                    **kwargs
                )
                session.add(device)
                session.commit()
                session.refresh(device)

            return device

    def add_sensor(
            self,
            device_id: int,
            capability: str,  # "switch", "temperature", "brightness"
            name: str,
            sensor_type: str = None,  # "relay", "ds18b20" и т.д.
            identifier: str = None,  # Для множественных сенсоров (например "light1")
            unit: str = None,
            icon: str = None,
            readonly: bool = False,
            min_value: float = None,
            max_value: float = None,
            **kwargs
    ) -> SensorEntity:
        """Добавить сенсор к устройству"""
        with write_session() as session:
            # Проверяем уникальность
            sensor = session.query(SensorEntity).filter_by(
                device_id=device_id,
                capability=capability,
                identifier=identifier
            ).first()

            if sensor:
                # Обновляем существующий
                for key, value in kwargs.items():
                    setattr(sensor, key, value)
                sensor.name = name
                sensor.unit = unit or None
                sensor.icon = icon or None
            else:
                sensor = SensorEntity(
                    device_id=device_id,
                    capability=capability,
                    identifier=identifier,
                    name=name,
                    type=sensor_type,
                    unit=unit,
                    icon=icon,
                    readonly=readonly,
                    min_value=min_value,
                    max_value=max_value,
                    **kwargs
                )
                session.add(sensor)

            session.commit()
            return sensor

    def update_sensor_value(
            self,
            sensor_id: int,
            value: Any
    ) -> SensorEntity:
        """Обновить значение сенсора (вызывается плагинами)"""
        return SensorRepository.update_sensor_value(sensor_id, value)

    def mark_device_ip_dead(self, device_id: int, ip: str):
        """
        Пометить IP как недоступный

        :param device_id: ID устройства
        :param ip: IP адрес, который не отвечает
        """
        self.ip_store.remove_ip(device_id, ip)

        # Если это был последний IP, пробуем обновить из БД
        if not self.ip_store.get_ip(device_id):
            self.update_device_ip_from_db(device_id)

    def remove_device(self, device_id: int):
        """Удалить устройство и все его сенсоры"""
        # Удаляем IP из кэша
        self.ip_store.remove_device(device_id)

        # Удаляем из БД
        with write_session() as session:
            device = session.get(DeviceEntity, device_id)
            if device:
                session.delete(device)
                session.commit()


device_registry = DeviceRegistry()
