from typing import Optional, List

from pydantic import BaseModel


class DeviceScanModelNetwork(BaseModel):
    """Сетевая информация устройства при сканировании"""
    device_id: Optional[str] = None  # external_id устройства
    name: Optional[str] = None  # имя интерфейса (eth0, wlan0)
    mac: Optional[str] = None
    ip: Optional[str] = None
    mask: Optional[str] = None
    gw: Optional[str] = None


class DeviceScanModel(BaseModel):
    """Модель устройства при сканировании"""
    plugin_id: int  # ID плагина в БД
    external_id: str  # Уникальный ID в системе плагина
    name: str  # Имя устройства

    # Опциональные поля
    type: Optional[str] = None  # Тип устройства
    capabilities: Optional[List[str]] = None
    networks: Optional[List[DeviceScanModelNetwork]] = None

    # Дополнительные данные (будут сохранены в device_registry)
    ip: Optional[str] = None
    port: Optional[int] = None
    extra: Optional[dict] = None
