# mds_scanner.py
import socket
from typing import Any, Optional, List, Callable
from datetime import datetime
from zeroconf import ServiceBrowser, ServiceListener, Zeroconf

from classes.logger.logger import logger
from plugins.core.umni_mdns.models.mdns_models import MDNSScanResult, MDNSDevice
from plugins.core.umni_mdns.classes.device_rest_commands import DeviceRestCommands


class MDNSScanner(ServiceListener):
    """Сканер mDNS с проверкой доступности через REST API"""

    def __init__(self, service_type: str = "_umni_api._tcp.local."):
        self.service_type = service_type
        self.scan_result = MDNSScanResult()
        self.logger = logger

        # ServiceBrowser будет запущен один раз
        self._browser: Optional[ServiceBrowser] = None
        self._is_running = False

        # Колбэки для событий
        self.on_device_added: Optional[Callable[[MDNSDevice], None]] = None
        self.on_device_removed: Optional[Callable[[str], None]] = None
        self.on_device_updated: Optional[Callable[[MDNSDevice, MDNSDevice], None]] = None
        self.on_device_offline: Optional[Callable[[MDNSDevice], None]] = None

    def start(self, zeroconf: Zeroconf):
        """Запускает ServiceBrowser один раз"""
        if self._is_running:
            self.logger.warning("ServiceBrowser already running")
            return

        self._browser = ServiceBrowser(zeroconf, self.service_type, self)
        self._is_running = True
        self.logger.debug(f"ServiceBrowser started for {self.service_type}")

    def stop(self):
        """Останавливает ServiceBrowser"""
        if self._browser:
            self._browser.cancel()
            self._browser = None
            self._is_running = False
            self.logger.debug("ServiceBrowser stopped")

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Обработчик добавления нового сервиса"""
        if type_ != self.service_type:
            return

        try:
            info = zc.get_service_info(type_, name)
            if not info:
                return

            device_data = self._parse_service_info(info, type_, name)
            if not device_data:
                return

            # Проверяем доступность устройства через REST API
            if self._check_device_online(device_data):
                device_data.update_timestamp()
                existing_device = self.scan_result.get_device(device_data.unique_id)

                if existing_device:
                    old_device = existing_device.model_copy()
                    device_data.first_seen = existing_device.first_seen
                    self.scan_result.add_device(device_data)

                    self.logger.debug(f"Device UPDATE: {device_data.name} -> {device_data.ip}:{device_data.port}")
                    if self.on_device_updated:
                        self.on_device_updated(old_device, device_data)
                else:
                    self.scan_result.add_device(device_data)
                    self.logger.debug(
                        f"Device ONLINE: {device_data.name} ({device_data.unique_id}) -> {device_data.ip}:{device_data.port}")

                    if self.on_device_added:
                        self.on_device_added(device_data)
            else:
                self.logger.debug(f"Device {device_data.name} ({device_data.ip}) not reachable via HTTP")

        except Exception as e:
            self.logger.error(f"Error add device {name}: {e}")
            self.scan_result.errors.append(f"Error add device {name}: {str(e)}")

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Обработчик обновления сервиса"""
        if type_ != self.service_type:
            return
        self.add_service(zc, type_, name)

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Обработчик удаления сервиса"""
        if type_ != self.service_type:
            return

        try:
            for device in self.scan_result.devices:
                if device.service_name == name:
                    unique_id = device.unique_id
                    self.scan_result.remove_device(unique_id)
                    self.logger.debug(f"Device REMOVED: {device.name} ({unique_id})")

                    if self.on_device_removed:
                        self.on_device_removed(unique_id)
                    break

        except Exception as e:
            self.logger.error(f"Error deleting device {name}: {e}")
            self.scan_result.errors.append(f"Error deleting device {name}: {str(e)}")

    def _parse_service_info(self, info: Any, type_: str, name: str) -> Optional[MDNSDevice]:
        """Парсит информацию о сервисе в модель MDNSDevice"""
        try:
            addresses = [socket.inet_ntoa(addr) for addr in info.addresses]
            primary_ip = addresses[0] if addresses else "0.0.0.0"

            txt_records = {}
            for k, v in info.properties.items():
                key = k.decode('utf-8') if isinstance(k, bytes) else k
                val = v.decode('utf-8') if isinstance(v, bytes) else v
                txt_records[key] = val

            unique_id = txt_records.get('unique_id', name.split('.')[0])
            device_name = txt_records.get('name', f"Device {unique_id}")
            server = info.server.decode('utf-8') if isinstance(info.server, bytes) else info.server

            return MDNSDevice(
                unique_id=unique_id,
                name=device_name,
                ip=primary_ip,
                port=info.port,
                service_type=type_,
                properties=txt_records,
                service_name=name,
                server=server,
                last_seen=datetime.now()
            )

        except Exception as e:
            self.logger.error(f"Error parsing service {name}: {e}")
            return None

    def _check_device_online(self, device: MDNSDevice) -> bool:
        """Проверяет доступность устройства через REST API"""
        try:
            # Создаем клиент для REST API
            client = DeviceRestCommands(
                ip_address=device.ip,
                timeout=3,
                protocol='http'
            )

            # Пробуем получить системную информацию
            result = client.get_system_info()

            # Проверяем, что ответ успешный
            return result.success

        except Exception as e:
            self.logger.debug(f"Device {device.name} ({device.ip}) is OFFLINE: {e}")
            return False

    # ========== Публичные методы ==========

    def get_devices(self) -> List[MDNSDevice]:
        """Возвращает список всех устройств"""
        return self.scan_result.devices.copy()

    def get_device_by_unique_id(self, unique_id: str) -> Optional[MDNSDevice]:
        """Возвращает устройство по unique_id"""
        return self.scan_result.get_device(unique_id)

    def get_devices_by_ip(self, ip: str) -> List[MDNSDevice]:
        """Возвращает устройства по IP"""
        return self.scan_result.get_devices_by_ip(ip)

    def get_online_devices(self) -> List[MDNSDevice]:
        """Возвращает онлайн устройства (проверяет через HTTP)"""
        online_devices = []
        for device in self.scan_result.devices:
            if self._check_device_online(device):
                device.update_timestamp()
                online_devices.append(device)
        return online_devices

    def get_offline_devices(self) -> List[MDNSDevice]:
        """Возвращает оффлайн устройства"""
        offline_devices = []
        for device in self.scan_result.devices:
            if not self._check_device_online(device):
                offline_devices.append(device)
        return offline_devices

    def cleanup_stale_devices(self, timeout_seconds: int = 60):
        """Удаляет устройства, которые не отвечают дольше timeout_seconds"""
        removed = []
        for device in self.scan_result.devices[:]:  # копия списка
            if not self._check_device_online(device):
                # Проверяем, сколько времени устройство оффлайн
                if (datetime.now() - device.last_seen).total_seconds() > timeout_seconds:
                    self.scan_result.remove_device(device.unique_id)
                    removed.append(device.unique_id)
                    self.logger.debug(f"Device cleaned (stale): {device.name}")
                    if self.on_device_removed:
                        self.on_device_removed(device.unique_id)
        return removed

    def clear_devices(self):
        """Очищает список устройств"""
        self.scan_result = MDNSScanResult()
        self.logger.debug("Devices cleared")

    def update_status(self) -> MDNSScanResult:
        """Обновляет статус всех устройств"""
        online = 0
        offline = 0

        for device in self.scan_result.devices:
            if self._check_device_online(device):
                device.update_timestamp()
                online += 1
            else:
                offline += 1

        self.scan_result.scan_finished = datetime.now()
        self.scan_result.total_count = len(self.scan_result.devices)

        self.logger.debug(f"Status: Online={online}, Offline={offline}, Total={self.scan_result.total_count}")

        return self.scan_result.model_copy()
