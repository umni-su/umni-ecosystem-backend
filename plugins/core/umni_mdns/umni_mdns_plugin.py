import threading
import time
from typing import Dict, Any, Optional, List

from zeroconf import Zeroconf

from classes.l10n.l10n import _
from classes.logger.logger import logger
from classes.logger.logger_types import LoggerType
from models.plugin_model import PluginModel
from plugins.base_plugin import BasePlugin, BasePluginConfig
from plugins.core.umni_mdns.classes.device_rest_commands import DeviceRestCommands
from plugins.core.umni_mdns.classes.mds_scanner import MDNSScanner
from plugins.core.umni_mdns.models.mdns_models import MDNSScanResult, MDNSDevice


class UmniMdnsConfig(BasePluginConfig):
    """Конфигурация плагина mDNS"""
    service_type: str = "_umni_api._tcp.local."
    health_check_interval: int = 30  # Интервал проверки статуса (сек)
    offline_timeout: int = 60  # Через сколько секунд считать устройство оффлайн

    def __init__(self, **data):
        super().__init__(**data)
        self.model_fields['service_type'].description = _('Service type')
        self.model_fields['health_check_interval'].description = _('Health check interval')
        self.model_fields['offline_timeout'].description = _('Offline timeout (seconds)')


class UmniMdnsPlugin(BasePlugin):
    """Плагин для мониторинга mDNS устройств UMNI"""

    config_class = UmniMdnsConfig
    plugin_name = "umni_mdns"

    def __init__(self, plugin_model: PluginModel):
        super().__init__(plugin_model)

        # Инициализация mDNS
        self.zeroconf = Zeroconf()
        self.scanner = MDNSScanner(self.config.service_type)

        # ЗАПУСКАЕМ ServiceBrowser ОДИН РАЗ
        self.scanner.start(self.zeroconf)

        # Настройка колбэков
        self.scanner.on_device_added = self._on_device_added
        self.scanner.on_device_removed = self._on_device_removed
        self.scanner.on_device_updated = self._on_device_updated

        # Поток для проверки статуса
        self._health_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        self.logger = logger

    def execute(self, data: Dict[str, Any] = None) -> Any:
        """Запускает периодическую проверку статуса устройств"""
        self.logger.debug(f"Plugin {self.name} started successfully")
        self._start_health_check()

    def on_stop(self):
        """Остановка плагина"""
        self._stop_health_check()
        self.scanner.stop()
        self.zeroconf.close()
        self.logger.debug(f"Plugin {self.name} stopped")
        super().on_stop()

    def on_config_update(self, new_config: Dict[str, Any]):
        """Обновление конфигурации"""
        super().on_config_update(new_config)

        # Обновляем service_type если изменился
        if self.is_running:
            self.scanner.service_type = self.config.service_type

    def set_sensor_value(
            self,
            external_id: str,
            capability: str,
            identifier: Optional[str],
            value: Any
    ) -> bool:
        """Установка значения сенсора"""
        self.logger.debug(f"Set sensor: {external_id}, {capability}, {value}")
        return True

    # ========== Внутренние методы ==========

    def _start_health_check(self):
        """Запускает периодическую проверку статуса"""
        if self._health_thread and self._health_thread.is_alive():
            return

        self._stop_event.clear()
        self._health_thread = threading.Thread(
            target=self._health_check_worker,
            daemon=True,
            name=f"HealthCheck-{self.name}"
        )
        self._health_thread.start()
        self.logger.debug(f"Health check started (interval: {self.config.health_check_interval}s)")

    def _stop_health_check(self):
        """Останавливает проверку статуса"""
        if not self._health_thread or not self._health_thread.is_alive():
            return

        self._stop_event.set()
        self._health_thread.join(timeout=5)
        self.logger.debug("Health check stopped")

    def _health_check_worker(self):
        """Рабочий поток для проверки статуса устройств"""
        while not self._stop_event.is_set():
            try:
                # Проверяем статус каждого устройства через HTTP
                self.scanner.update_status()

                # Получаем оффлайн устройства
                offline_devices = self.scanner.get_offline_devices()
                if offline_devices:
                    self.logger.debug(f"Offline devices: {len(offline_devices)}")
                    for device in offline_devices:
                        self._on_device_offline(device)

                # Получаем онлайн устройства
                online_devices = self.scanner.get_online_devices()
                if online_devices:
                    self.logger.debug(f"Online devices: {len(online_devices)}")

                # Очищаем давно оффлайн устройства
                removed = self.scanner.cleanup_stale_devices(self.config.offline_timeout)
                if removed:
                    self.logger.debug(f"Removed stale devices: {removed}")

                # Ждем интервал или сигнал остановки
                self._stop_event.wait(self.config.health_check_interval)

            except Exception as e:
                self.logger.error(f"Error in health check: {e}")
                time.sleep(60)

    # ========== Колбэки ==========

    def _on_device_added(self, device: MDNSDevice):
        """Новое устройство обнаружено"""
        self.logger.info(f"✅ Device ONLINE: {device.name} ({device.unique_id}) -> {device.ip}:{device.port}")
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
            self.logger.error(str(e), LoggerType.PLUGINS)

    def _on_device_removed(self, unique_id: str):
        """Устройство удалено из mDNS"""
        self.logger.info(f"❌ Device REMOVED: {unique_id}")

    def _on_device_updated(self, old_device: MDNSDevice, new_device: MDNSDevice):
        """Данные устройства обновлены"""
        if old_device.ip != new_device.ip:
            self.logger.info(f"🔄 Device IP changed: {old_device.name} ({old_device.ip} -> {new_device.ip})")
        else:
            self.logger.debug(f"🔄 Device updated: {new_device.name}")

    def _on_device_offline(self, device: MDNSDevice):
        """Устройство стало оффлайн (не отвечает)"""
        self.logger.warning(f"⚠️ Device OFFLINE: {device.name} ({device.unique_id}) - last seen: {device.last_seen}")
        self.manager.registry.set_offline(device.unique_id)

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
