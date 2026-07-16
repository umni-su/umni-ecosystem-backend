import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, Any, Optional, List

from zeroconf import Zeroconf

from classes.l10n.l10n import _
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from models.device_model_relations import DeviceModelWithRelations
from models.device_scan_model import DeviceScanModelNetwork, DeviceScanModel
from models.plugin_model import PluginModel
from plugins.base_plugin import BasePlugin, BasePluginConfig
from plugins.core.umni_mdns.classes.device_rest_commands import DeviceRestCommands
from plugins.core.umni_mdns.classes.device_synchronizer import DeviceSynchronizer
from plugins.core.umni_mdns.classes.mds_scanner import MDNSScanner
from plugins.core.umni_mdns.classes.syslog_listener import SyslogListener, SyslogMessage
from plugins.core.umni_mdns.models.mdns_models import MDNSScanResult, MDNSDevice
from repositories.device_repository import DeviceRepository


class UmniMdnsConfig(BasePluginConfig):
    """Конфигурация плагина mDNS"""
    service_type: str = "_umni_api._tcp.local."
    health_check_interval: int = 30  # Интервал проверки статуса (сек)
    offline_timeout: int = 300  # Через сколько секунд считать устройство оффлайн
    syslog_port: int = 514
    syslog_addr: str = "0.0.0.0"

    def __init__(self, **data):
        super().__init__(**data)
        self.model_fields['service_type'].description = _('Service type')
        self.model_fields['health_check_interval'].description = _('Health check interval')
        self.model_fields['offline_timeout'].description = _('Offline timeout (seconds)')


class UmniMdnsPlugin(BasePlugin):
    """Плагин для мониторинга mDNS устройств UMNI"""

    config_class = UmniMdnsConfig
    plugin_name = "umni_mdns"
    syslog: SyslogListener

    def __init__(self, plugin_model: 'PluginModel'):
        super().__init__(plugin_model)
        self.chunk_size = 20
        self._stop_event = threading.Event()
        self._health_thread = None
        self._executor = ThreadPoolExecutor(max_workers=20)

        # Кэш для отслеживания последней синхронизации
        self._last_sync_cache: Dict[int, datetime] = {}
        self._sync_interval = 300  # 5 минут

        self.zeroconf = Zeroconf()
        self.scanner = MDNSScanner(self.config.service_type)
        self.scanner.start(self.zeroconf)

        self.run_syslog()

    def run_syslog(self):
        self.syslog = SyslogListener(
            host=self.config.syslog_addr,
            port=self.config.syslog_port
        )

        def new_syslog_message(msg: SyslogMessage):
            pass
            # Logger.debug(f"SYSLOG [{msg.timestamp.strftime('%H:%M:%S')}] "
            #              f"{msg.source_host}:{msg.source_port} "
            #              f"{msg.device_name} [{msg.topic}] "
            #              f"data: {msg.data}", LoggerType.PLUGINS)

        self.syslog.add_handler(new_syslog_message)
        self.syslog.start()

    def execute(self, data: Dict[str, Any] = None) -> Any:
        """Фоновая задача - обновление статуса устройств"""

        self._sync_devices_from_db()

        self.scanner.update_status()

        self._start_health_check()

        self.run_syslog()

        return {
            "status": "running",
            "total_devices": len(self.scanner.get_devices()),
            "online": len(self.scanner.get_online_devices()),
            "offline": len(self.scanner.get_offline_devices())
        }

    def on_stop(self):
        """Остановка плагина"""
        self._stop_health_check()
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False, cancel_futures=True)
        self.scanner.stop()
        self.zeroconf.close()
        self.syslog.stop()
        Logger.debug(f"Plugin {self.name} stopped")
        super().on_stop()

    def on_config_update(self, new_config: Dict[str, Any]):
        """Обновление конфигурации"""
        super().on_config_update(new_config)

        # Обновляем service_type если изменился
        if self.is_running:
            self.scanner.service_type = self.config.service_type

    def scan_devices(self) -> List[DeviceScanModel]:
        """
        Сканирование устройств через mDNS.
        Вызывается из API.
        """
        devices = []

        for mdns_device in self.scanner.get_devices():
            # Проверяем доступность
            if not self._check_port(
                    ip=mdns_device.ip,
                    port=mdns_device.port
            ):
                continue

            # Получаем системную информацию
            controller = DeviceRestCommands(mdns_device.ip)
            sys_info = controller.get_system_info()

            # Формируем модель устройства
            device = DeviceScanModel(
                plugin_id=self.db_id,
                external_id=mdns_device.unique_id,
                name=mdns_device.name,
                type=self.name,
                ip=mdns_device.ip,
                port=mdns_device.port,
                extra={
                    'service_name': mdns_device.service_name,
                    'server': mdns_device.server
                }
            )

            # Добавляем capabilities если есть
            if sys_info.success and sys_info.data:
                device.capabilities = [cap.value for cap in sys_info.data.capabilities]

                # Добавляем сетевую информацию
                device.networks = []
                for net in sys_info.data.networks:
                    device.networks.append(
                        DeviceScanModelNetwork(
                            device_id=mdns_device.unique_id,
                            name=net.name,
                            mac=net.mac,
                            ip=net.ip,
                            mask=net.mask,
                            gw=net.gw
                        )
                    )

            devices.append(device)
            Logger.info(f"Scanned device: {mdns_device.name} ({mdns_device.ip})")

        return devices

    def get_plugin_devices(self) -> List[DeviceModelWithRelations]:
        return DeviceRepository.get_device_by_plugin_id(
            plugin_id=self.db_id
        )

    def set_sensor_value(
            self,
            external_id: str,
            capability: str,
            identifier: Optional[str],
            value: Any
    ) -> bool:
        """Установка значения сенсора"""
        Logger.debug(f"Set sensor: {external_id}, {capability}, {value}")
        return True

    # ========== Внутренние методы ==========

    def _sync_devices_from_db(self):
        """Синхронизирует устройства из БД с mDNS сканером"""
        try:
            # Получаем все устройства этого плагина из БД
            devices = self.repository.get_device_by_plugin_id(self.db_id)

            if not devices:
                Logger.debug("No devices in DB to sync")
                return

            Logger.info(f"Syncing {len(devices)} devices from database")

            for device in devices:
                # Проверяем, есть ли уже такое устройство в сканере
                existing = self.scanner.get_device_by_unique_id(
                    unique_id=device.external_id
                )

                if not existing:
                    mdns_device = MDNSDevice(
                        unique_id=device.external_id,
                        name=device.name,
                        ip=self.manager.registry.get_device_ip(device.id) or "0.0.0.0",
                        port=80,  # default port
                        service_type=self.config.service_type,
                        properties={},
                        service_name=device.external_id,
                        server=device.external_id,
                        last_seen=device.last_sync
                    )

                    # Добавляем в сканер
                    self.scanner.scan_result.add_device(mdns_device)
                    Logger.debug(f"Restored device from DB: {device.name} ({device.external_id})")

        except Exception as e:
            Logger.err(f"Error syncing devices from DB: {e}")

    def _start_health_check(self):
        """Запускает периодическую проверку статуса"""
        if self._health_thread and self._health_thread.is_alive():
            return
        if self._stop_event:
            self._stop_event.clear()
        self._health_thread = threading.Thread(
            target=self._health_check_worker,
            daemon=True,
            name=f"HealthCheck-{self.name}"
        )
        self._health_thread.start()
        Logger.debug(f"Health check started (interval: {self.config.health_check_interval}s)")

    def _stop_health_check(self):
        """Останавливает проверку статуса"""
        if not self._health_thread or not self._health_thread.is_alive():
            return

        if self._stop_event:
            self._stop_event.set()

        self._health_thread.join(timeout=5)
        Logger.debug("Health check stopped")

    def _health_check_worker(self):
        """Рабочий поток для проверки статуса устройств"""
        while not self._stop_event.is_set():
            try:
                # Проверяем, не завершается ли интерпретатор
                if self._executor._shutdown:
                    Logger.debug("Executor shut down, exiting health check")
                    break

                devices = self.get_plugin_devices()
                self._check_devices_parallel(devices)

                # Используем wait с таймаутом
                self._stop_event.wait(self.config.health_check_interval)

            except RuntimeError as e:
                if "interpreter shutdown" in str(e) or "cannot schedule new futures" in str(e):
                    Logger.debug("Interpreter shutdown detected, exiting")
                    break
                Logger.err(f"Error in health check: {e}", LoggerType.PLUGINS)
                time.sleep(self.config.health_check_interval)
            except Exception as e:
                Logger.err(f"Error in health check: {e}", LoggerType.PLUGINS)
                time.sleep(self.config.health_check_interval)

        Logger.debug("Health check worker stopped")

    def _check_devices_parallel(self, devices: List[DeviceModelWithRelations]):
        """Параллельная проверка устройств"""
        # Проверяем, что executor еще работает
        if not self._executor or self._executor._shutdown:
            Logger.debug("Executor is shut down, skipping check")
            return

        chunk_size = self.chunk_size
        chunks = [devices[i:i + chunk_size] for i in range(0, len(devices), chunk_size)]

        for chunk in chunks:
            # Проверяем stop_event
            if self._stop_event.is_set():
                Logger.debug("Stop event set, canceling checks")
                return

            futures = []
            for device in chunk:
                if self._stop_event.is_set():
                    break
                try:
                    future = self._executor.submit(self._check_single_device, device)
                    futures.append(future)
                except RuntimeError as e:
                    if "cannot schedule new futures" in str(e):
                        Logger.debug("Cannot submit task (interpreter shutting down)")
                        return
                    raise

            for future in futures:
                if self._stop_event.is_set():
                    break
                try:
                    future.result(timeout=10)
                except Exception as e:
                    Logger.debug(f"Device check error: {e}")

    def _check_single_device(self, device: DeviceModelWithRelations):
        mdns_device = self.scanner.get_device_by_unique_id(device.external_id)
        # TODO make retries
        if not mdns_device:
            if device.online:
                self.manager.registry.set_offline(device.external_id)
                Logger.err(
                    f'[ID{device.id}, {device.external_id}] Failed to check (not found in mdns scanner repository)',
                    LoggerType.PLUGINS)
            return

        if not self._check_port(
                ip=mdns_device.ip,
                port=mdns_device.port
        ):
            if device.online:
                self.manager.registry.set_offline(device.external_id)
                Logger.err(f'[ID{device.id}, {device.external_id}] Failed to check (telnet error)', LoggerType.PLUGINS)
            return

        Logger.debug(f'[ID{device.id}, {device.external_id}] Successfully checked by telnet', LoggerType.PLUGINS)

        # TODO other checks

        saver = DeviceSynchronizer(
            mdns_info=mdns_device,
            device=device
        )

        saver.sync_device()

    def _check_port(self, ip: str, port: int, timeout: float = 1.5) -> bool:
        """Быстрая проверка порта (telnet)"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except:
            return False

    # ========== Колбэки ==========

    def _on_device_added(self, device: MDNSDevice):
        """Новое устройство обнаружено"""
        Logger.info(f"Device ONLINE: {device.name} ({device.unique_id}) -> {device.ip}:{device.port}")
        controller = DeviceRestCommands(
            ip_address=device.ip
        )
        try:
            _system_info = controller.get_system_info()
            if _system_info.success is True:
                self.manager.registry.register_device(
                    plugin_id=self.db_id,
                    name=_system_info.data.hostname,
                    external_id=_system_info.data.hostname,
                    capabilities=_system_info.data.capabilities,
                    free_heap=_system_info.data.heap.free,
                    total_heap=_system_info.data.heap.total
                )
        except Exception as e:
            Logger.err(str(e), LoggerType.PLUGINS)

    def _on_device_removed(self, unique_id: str):
        """Устройство удалено из mDNS"""
        Logger.info(f"Device REMOVED: {unique_id}")

    def _on_device_updated(self, old_device: MDNSDevice, new_device: MDNSDevice):
        """Данные устройства обновлены"""
        if old_device.ip != new_device.ip:
            Logger.info(f"Device IP changed: {old_device.name} ({old_device.ip} -> {new_device.ip})")
        else:
            Logger.debug(f"Device updated: {new_device.name}")

    def _on_device_status_change(self, device: MDNSDevice, is_online: bool):
        """Общий обработчик изменения статуса"""
        if is_online:
            self.manager.registry.set_online(device.unique_id)
        else:
            self.manager.registry.set_offline(device.unique_id)

    def _on_device_offline(self, device: MDNSDevice):
        """Устройство стало оффлайн (не отвечает)"""
        self._on_device_status_change(device, False)
        Logger.warn(f"Device OFFLINE: {device.name} ({device.unique_id}) - last seen: {device.last_seen}")

    def _on_device_online(self, device: MDNSDevice):
        """Устройство стало оффлайн (не отвечает)"""
        self._on_device_status_change(device, True)
        Logger.debug(f"Device ONLINE: {device.name} ({device.unique_id}) - last seen: {device.last_seen}")

    # ========== Публичные методы ==========

    def get_devices(self) -> List[MDNSDevice]:
        """Все устройства"""
        return self.scanner.get_devices()

    def get_online_devices(self) -> List[MDNSDevice]:
        """Онлайн устройства"""
        return self.scanner.get_online_devices()

    def get_offline_devices(self) -> List[MDNSDevice]:
        """Оффлайн устройства"""
        return self.scanner.get_offline_devices()

    def get_device(self, unique_id: str) -> Optional[MDNSDevice]:
        """Устройство по ID"""
        return self.scanner.get_device_by_unique_id(unique_id)

    def get_devices_by_ip(self, ip: str) -> List[MDNSDevice]:
        """Устройства по IP"""
        return self.scanner.get_devices_by_ip(ip)

    def force_refresh(self) -> MDNSScanResult:
        """Принудительное обновление статуса"""
        return self.scanner.update_status()
