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

import json
import urllib.error
import urllib.request
import urllib.parse
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field, AnyHttpUrl, field_validator
from enum import IntEnum, Enum


# ============ Enum Definitions ============

class AuthMode(IntEnum):
    """Режимы аутентификации WiFi"""
    OPEN = 0
    WEP = 1
    WPA_PSK = 2
    WPA2_PSK = 3
    WPA_WPA2_PSK = 4
    WPA2_ENTERPRISE = 5
    WPA3_PSK = 6
    WPA2_WPA3_PSK = 7


class IPType(IntEnum):
    """Тип получения IP адреса"""
    DHCP = 1
    STATIC = 2


class NetworkMode(IntEnum):
    """Режим сети"""
    ETH = 1
    WIFI_AP = 2


class SwitchMode(str, Enum):
    OUTPUTS = "outputs"
    OPENCOLLECTORS = "opencollectors"


class APIError(Exception):
    """Базовое исключение для ошибок API"""

    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(message)


class ConnectionError(APIError):
    """Ошибка соединения"""
    pass


class HTTPError(APIError):
    """HTTP ошибка"""
    pass


class ParseError(APIError):
    """Ошибка парсинга JSON"""
    pass


# ============ Base Response ============

class ResponseBase(BaseModel):
    """Базовый класс для всех ответов API"""
    success: bool
    status_code: Optional[int] = Field(None, description="HTTP статус код")

    class Config:
        extra = 'allow'  # Разрешаем дополнительные поля


# ============ System Info Models ============

class NetworkInfo(BaseModel):
    """Информация о сетевом подключении"""
    name: Literal['ethernet', 'wifi']
    mac: str
    ip: str = Field(..., pattern=r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
    mask: str = Field(..., pattern=r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
    gw: str = Field(..., pattern=r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
    active: bool


class HeapInfo(BaseModel):
    """Информация о куче памяти"""
    total: int
    free: int
    min: int


class Capability(str, Enum):
    """Возможности контроллера"""
    ETHERNET = 'ethernet'
    WIFI = 'wifi'
    SDCARD = 'sdcard'
    WEBSERVER = 'webserver'
    WEBHOOKS = 'webhooks'  # Добавляем
    MQTT = 'mqtt'
    OPENTHERM = 'opentherm'
    RF433 = 'rf433'
    ONEWIRE = 'onewire'
    ALARM = 'alarm'
    NTC = 'ntc'  # Добавляем общий
    NTC1 = 'ntc1'
    NTC2 = 'ntc2'
    AI = 'ai'  # Добавляем общий
    AI1 = 'ai1'
    AI2 = 'ai2'
    OPENCOLLECTORS = 'opencollectors'
    OC1 = 'oc1'
    OC2 = 'oc2'
    BUZZER = 'buzzer'
    INPUTS = 'inputs'
    INP1 = 'inp1'
    INP2 = 'inp2'
    INP3 = 'inp3'
    INP4 = 'inp4'
    INP5 = 'inp5'
    INP6 = 'inp6'
    OUTPUTS = 'outputs'
    OUT1 = 'out1'
    OUT2 = 'out2'
    OUT3 = 'out3'
    OUT4 = 'out4'
    OUT5 = 'out5'
    OUT6 = 'out6'
    OUT7 = 'out7'
    OUT8 = 'out8'


class SystemInfoData(BaseModel):
    """Данные системной информации"""
    hostname: str
    capabilities: List[Capability]
    networks: List[NetworkInfo]
    heap: HeapInfo


class SystemInfoResponse(ResponseBase):
    """Ответ системной информации"""
    data: Optional[SystemInfoData] = None


# ============ DIO Models ============

class DIOInput(BaseModel):
    """Цифровой вход"""
    config_index: int = Field(ge=1)
    port_index: int = Field(ge=0)
    label: str
    active: bool


class DIOOutput(BaseModel):
    """Цифровой выход"""
    config_index: int = Field(ge=1)
    port_index: int = Field(ge=0)
    label: str
    active: bool
    default_state: Literal[0, 1] = 0


class DIOData(BaseModel):
    """Данные DIO"""
    inputs: List[DIOInput]
    outputs: List[DIOOutput]


class DIOInfoResponse(ResponseBase):
    """Ответ DIO информации"""
    data: Optional[DIOData] = None


# ============ ADC Models ============

class ADCChannel(BaseModel):
    """ADC канал"""
    id: int = Field(ge=0)
    label: str
    active: bool


class ADCData(BaseModel):
    """Данные ADC"""
    channels: List[ADCChannel]


class ADCInfoResponse(ResponseBase):
    """Ответ ADC информации"""
    data: Optional[ADCData] = None


# ============ NTC Models ============

class NTCChannel(BaseModel):
    """NTC канал"""
    id: int = Field(ge=0)
    label: str
    active: bool


class NTCData(BaseModel):
    """Данные NTC"""
    channels: List[NTCChannel]


class NTCInfoResponse(ResponseBase):
    """Ответ NTC информации"""
    data: Optional[NTCData] = None


# ============ OneWire Models ============

class OneWireSensor(BaseModel):
    """OneWire датчик"""
    sn: str = Field(..., min_length=16, max_length=16)
    label: str
    active: bool


class OneWireData(BaseModel):
    """Данные OneWire"""
    sensors: List[OneWireSensor]


class OneWireInfoResponse(ResponseBase):
    """Ответ OneWire информации"""
    data: Optional[OneWireData] = None


# ============ RF433 Models ============

class RF433Device(BaseModel):
    """RF433 устройство"""
    mode: Optional[Literal['delete']] = None
    serial: int
    label: str
    alaram: bool
    type: int


class RF433Data(BaseModel):
    """Данные RF433"""
    devices: List[RF433Device]


class RF433InfoResponse(ResponseBase):
    """Ответ RF433 информации"""
    data: Optional[RF433Data] = None


# ============ Opentherm Models ============

class OpenthermControlType(str, Enum):
    """Тип управления Opentherm"""
    ON_OFF = "ON/OFF"
    MODULATING = "MODULATING"


class OpenthermDHWConfig(str, Enum):
    """Конфигурация ГВС"""
    INSTANTANEOUS = "INSTANTANEOUS"
    STORAGE = "STORAGE"
    UNKNOWN = "UNKNOWN"


class OpenthermBoilerConfig(BaseModel):
    """Конфигурация котла"""
    control_type: OpenthermControlType
    dhw_present: bool
    dhw_config: OpenthermDHWConfig
    ch2_present: bool
    cooling_supported: bool
    pump_control_allowed: bool
    slave_ot_version: int
    slave_product_version: int


class OpenthermBounds(BaseModel):
    """Границы значений"""
    min: float
    max: float


class OpenthermBoundsData(BaseModel):
    """Данные границ"""
    ch: OpenthermBounds
    dhw: OpenthermBounds
    heat_curve: OpenthermBounds


class OpenthermState(BaseModel):
    """Состояние Opentherm"""
    ot_enabled: bool
    ready: bool
    adapter_success: bool
    status_code: int
    ch_enable: bool
    ch_setpoint_requested: int
    dhw_enable: bool
    dhw_setpoint_requested: int
    otc_enable: bool
    cooling_enable: bool
    ch2_enable: bool
    modulation_level_set: int
    heat_curve_ratio: int
    central_heating_active: bool
    hot_water_active: bool
    flame_on: bool
    is_fault: bool
    boiler_temperature: float
    return_temperature: float
    dhw_temperature: float
    outside_temperature: float
    dhw_setpoint_current: float
    ch_max_setpoint: float
    modulation: int
    pressure: float
    flow_rate: float
    flow_rate_ch2: float
    fault_code: int
    boiler_config: OpenthermBoilerConfig
    bounds: OpenthermBoundsData


class OpenthermData(BaseModel):
    """Данные Opentherm"""
    state: OpenthermState


class OpenthermInfoResponse(ResponseBase):
    """Ответ Opentherm информации"""
    data: Optional[OpenthermData] = None


# ============ Switch Models ============

class SwitchRequest(BaseModel):
    """Запрос на переключение выхода"""
    mode: SwitchMode
    index: int = Field(ge=1)
    level: bool


class SwitchData(BaseModel):
    """Данные ответа переключения"""
    mode: str
    index: int
    level: bool
    status: str


class SwitchResponse(ResponseBase):
    """Ответ на переключение"""
    data: Optional[SwitchData] = None


# ============ Settings Models ============

class MQTTSettings(BaseModel):
    """Настройки MQTT"""
    en: bool
    host: str
    port: int = Field(ge=0, le=65535)
    user: Optional[str] = None
    password: Optional[str] = None


class WebhookSettings(BaseModel):
    """Настройки Webhook"""
    en: bool
    url: AnyHttpUrl


class OutputSettings(BaseModel):
    """Настройки выхода"""
    en: bool
    label: Optional[str] = None
    index: int
    default_state: Optional[Literal[0, 1]] = None


class InputSettings(BaseModel):
    """Настройки входа"""
    en: bool
    label: Optional[str] = None
    index: int


class NTCSettings(BaseModel):
    """Настройки NTC"""
    channel: int = Field(ge=0)
    active: bool
    offset: float = 0.0
    label: str


class ADCSettings(BaseModel):
    """Настройки ADC"""
    channel: int = Field(ge=0)
    active: bool
    offset: float = 0.0
    label: str


class OneWireSettings(BaseModel):
    """Настройки OneWire"""
    serial: str = Field(..., min_length=16, max_length=16)
    label: str
    active: bool
    calibration: float = 0.0


class RF433Settings(BaseModel):
    """Настройки RF433"""
    mode: Optional[Literal['delete']] = None
    serial: int
    label: str
    alaram: bool
    type: int


class OpenthermSettings(BaseModel):
    """Настройки Opentherm"""
    en: bool
    ch_en: bool
    ch_sp: int
    dhw_en: bool
    dhw_sp: int
    ch2_en: bool
    cool_en: bool
    mod: int = Field(ge=0, le=100)
    otc_en: bool


class SettingsRequest(BaseModel):
    """Запрос на обновление настроек"""
    setting: Literal['mqtt', 'webhook', 'outputs', 'inputs', 'ntc', 'adc', 'onewire', 'rf433', 'opentherm']
    values: Dict[str, Any]


class SettingsData(BaseModel):
    """Данные ответа настроек"""
    setting: str
    values: Dict[str, Any]
    status: str


class SettingsResponse(ResponseBase):
    """Ответ на обновление настроек"""
    data: Optional[SettingsData] = None


# ============ Configuration Models ============

class WiFiAPSettings(BaseModel):
    """Настройки WiFi AP"""
    wifi_ap_ssid: Optional[str] = None
    wifi_ap_password: Optional[str] = None
    wifi_ap_channel: Optional[int] = Field(None, ge=1, le=13)
    wifi_ap_max_connections: Optional[int] = Field(None, ge=1, le=10)
    wifi_ap_hidden: Optional[bool] = None


class WiFiSTASettings(BaseModel):
    """Настройки WiFi STA"""
    wifi_sta_ssid: Optional[str] = None
    wifi_sta_password: Optional[str] = None
    wifi_sta_ip_type: Optional[IPType] = None
    wifi_sta_ip: Optional[str] = Field(None, pattern=r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
    wifi_sta_netmask: Optional[str] = Field(None, pattern=r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
    wifi_sta_gateway: Optional[str] = Field(None, pattern=r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
    wifi_sta_dns: Optional[str] = Field(None, pattern=r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')


class EthernetSettings(BaseModel):
    """Настройки Ethernet"""
    eth_ip_type: Optional[IPType] = None
    eth_ip: Optional[str] = Field(None, pattern=r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
    eth_netmask: Optional[str] = Field(None, pattern=r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
    eth_gateway: Optional[str] = Field(None, pattern=r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
    eth_dns: Optional[str] = Field(None, pattern=r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')


class SystemSettings(BaseModel):
    """Системные настройки"""
    title: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    ntp: Optional[str] = None
    timezone: Optional[str] = None
    socket_port: Optional[int] = Field(None, ge=1, le=65535)
    token: Optional[str] = None
    network_mode: Optional[NetworkMode] = None


class FullConfiguration(SystemSettings, WiFiSTASettings, WiFiAPSettings, EthernetSettings):
    """Полная конфигурация устройства"""
    pass


class ConfigurationData(BaseModel):
    """Данные конфигурации"""
    title: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    ntp: Optional[str] = None
    timezone: Optional[str] = None
    socket_port: Optional[int] = None
    token: Optional[str] = None
    network_mode: Optional[int] = None
    wifi_sta_ssid: Optional[str] = None
    wifi_sta_password: Optional[str] = None
    wifi_sta_ip_type: Optional[int] = None
    wifi_sta_ip: Optional[str] = None
    wifi_sta_netmask: Optional[str] = None
    wifi_sta_gateway: Optional[str] = None
    wifi_sta_dns: Optional[str] = None
    wifi_ap_ssid: Optional[str] = None
    wifi_ap_password: Optional[str] = None
    eth_ip_type: Optional[int] = None
    eth_ip: Optional[str] = None
    eth_netmask: Optional[str] = None
    eth_gateway: Optional[str] = None
    eth_dns: Optional[str] = None


class ConfigurationResponse(ResponseBase):
    """Ответ конфигурации"""
    data: Optional[ConfigurationData] = None


# ============ WiFi Scan Models ============

class WiFiNetwork(BaseModel):
    """WiFi сеть"""
    ssid: str
    rssi: int
    channel: int = Field(ge=1, le=13)
    authmode: int
    authmode_name: str


class WiFiScanResponse(ResponseBase):
    """Ответ сканирования WiFi"""
    data: Optional[List[WiFiNetwork]] = None


# ============ Beep Models ============

class BeepRequest(BaseModel):
    """Запрос на звуковой сигнал"""
    count: int = Field(ge=1)
    on_ms: int = Field(ge=0, le=1000)
    off_ms: int = Field(ge=0, le=1000)

    @field_validator('count')
    @classmethod
    def validate_count(cls, v):
        if v < 1:
            raise ValueError('count must be >= 1')
        return v


class BeepData(BaseModel):
    """Данные ответа звукового сигнала"""
    count: int
    on_ms: int
    off_ms: int
    status: str


class BeepResponse(ResponseBase):
    """Ответ на звуковой сигнал"""
    data: Optional[BeepData] = None


# ============ State Models ============

class StateValue(BaseModel):
    """Значение состояния"""
    value: float


class StateHistory(BaseModel):
    """История состояния"""
    name: str
    timestamps: List[int]
    values: List[float]
    count: int


class StateData(BaseModel):
    """Данные состояния"""
    state: StateValue
    history: StateHistory


class StateResponse(ResponseBase):
    """Ответ состояния"""
    data: Optional[StateData] = None


# ============ Automation Models ============

class Condition(BaseModel):
    """Условие автоматизации"""
    capability: str
    op: Literal['>', '<', '>=', '<=', '==', '!=']
    value: float
    subtype: Optional[str] = None


class Action(BaseModel):
    """Действие автоматизации"""
    capability: str
    action: Any
    subtype: Optional[str] = None


class Automation(BaseModel):
    """Автоматизация"""
    id: int
    if_: Condition = Field(alias='if')
    then: List[Action]
    else_: Optional[List[Action]] = Field(None, alias='else')

    class Config:
        populate_by_name = True


class AutomationData(BaseModel):
    """Данные автоматизаций"""
    automations: List[Automation]


class AutomationResponse(ResponseBase):
    """Ответ списка автоматизаций"""
    data: Optional[List[Automation]] = None


class AutomationCreateRequest(BaseModel):
    """Запрос на создание автоматизации"""
    if_: Condition = Field(alias='if')
    then: List[Action]
    else_: Optional[List[Action]] = Field(None, alias='else')

    class Config:
        populate_by_name = True


class AutomationCreateResponse(ResponseBase):
    """Ответ создания автоматизации"""
    data: Optional[Automation] = None


class AutomationUpdateResponse(ResponseBase):
    """Ответ обновления автоматизации"""
    data: Optional[Automation] = None


class AutomationDeleteResponse(ResponseBase):
    """Ответ удаления автоматизации"""
    data: Optional[Dict[str, Any]] = None


# ============ Main Client Class ============

class DeviceRestCommands:
    def __init__(self, ip_address: str, timeout: int = 10, protocol: str = 'http', token: Optional[str] = None):
        """
        Инициализация клиента

        :param ip_address: IP адрес контроллера
        :param timeout: Таймаут запроса в секундах
        :param protocol: Протокол (http или https)
        :param token: Токен авторизации (если установлен)
        """
        self.ip = ip_address
        self.protocol = protocol
        self.timeout = timeout
        self.token = token
        self.base_url = f"{protocol}://{ip_address}"

    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None,
                 params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Внутренний метод для выполнения запросов
        :return: Ответ от API в виде словаря
        :raises: APIError, ConnectionError, HTTPError, ParseError
        """
        url = f"{self.base_url}{endpoint}"
        if params:
            url += "?" + urllib.parse.urlencode(params)

        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        # Подготовка данных
        if data is not None:
            json_data = json.dumps(data, default=lambda x: x.value if isinstance(x, Enum) else x).encode('utf-8')
            req = urllib.request.Request(url, data=json_data, headers=headers, method=method)
        else:
            req = urllib.request.Request(url, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                response_data = response.read().decode('utf-8')
                result = json.loads(response_data)
                result['status_code'] = response.getcode()
                return result

        except urllib.error.HTTPError as e:
            try:
                error_body = e.read().decode('utf-8')
                error_json = json.loads(error_body)
                raise HTTPError(
                    message=error_json.get('error', str(e)),
                    status_code=e.code,
                    response_data=error_json
                )
            except json.JSONDecodeError:
                raise HTTPError(
                    message=f"HTTP {e.code}: {e.reason}",
                    status_code=e.code
                )

        except urllib.error.URLError as e:
            raise ConnectionError(
                message=f"Connection error with {self.ip}: {e}",
                status_code=None
            )

        except json.JSONDecodeError as e:
            raise ParseError(
                message=f"Invalid JSON response: {e}",
                status_code=None
            )

    # ============ GET Methods ============

    def get_system_info(self) -> SystemInfoResponse:
        """Получение системной информации"""
        return SystemInfoResponse(**self._request('GET', '/api/systeminfo'))

    def get_dio_info(self) -> DIOInfoResponse:
        """Получение информации о цифровых входах/выходах"""
        return DIOInfoResponse(**self._request('GET', '/api/dio'))

    def get_adc_info(self) -> ADCInfoResponse:
        """Получение информации об аналоговых входах"""
        return ADCInfoResponse(**self._request('GET', '/api/adc'))

    def get_ntc_info(self) -> NTCInfoResponse:
        """Получение информации о NTC датчиках"""
        return NTCInfoResponse(**self._request('GET', '/api/ntc'))

    def get_onewire_info(self) -> OneWireInfoResponse:
        """Получение информации о OneWire датчиках"""
        return OneWireInfoResponse(**self._request('GET', '/api/onewire'))

    def get_rf433_info(self) -> RF433InfoResponse:
        """Получение информации об RF433 устройствах"""
        return RF433InfoResponse(**self._request('GET', '/api/rf433'))

    def get_opentherm_info(self) -> OpenthermInfoResponse:
        """Получение информации о состоянии Opentherm"""
        return OpenthermInfoResponse(**self._request('GET', '/api/opentherm'))

    def get_configuration(self, section: Optional[
        Literal['adc', 'ntc', 'dio', 'onewire', 'rf433']] = None) -> ConfigurationResponse:
        """
        Получение конфигурации устройства или секции

        :param section: Секция конфигурации
        """
        params = {}
        if section:
            params['section'] = section
        return ConfigurationResponse(**self._request('GET', '/api/conf', params=params))

    def get_full_configuration(self) -> ConfigurationResponse:
        """Получение полной конфигурации устройства"""
        return ConfigurationResponse(**self._request('GET', '/api/configuration'))

    def get_automations(self) -> AutomationResponse:
        """Получение списка автоматизаций"""
        return AutomationResponse(**self._request('GET', '/api/automations'))

    def get_state(self, capability: str) -> StateResponse:
        """
        Получение состояния сенсора

        :param capability: Имя capability (ntc1, ntc2, ai1, ai2, opentherm)
        """
        data = {"capability": capability}
        return StateResponse(**self._request('POST', '/api/state', data=data))

    # ============ POST Methods ============

    def update_settings(self, setting: Literal[
        'mqtt', 'webhook', 'outputs', 'inputs', 'ntc', 'adc', 'onewire', 'rf433', 'opentherm'],
                        values: Dict[str, Any]) -> SettingsResponse:
        """
        Обновление настроек контроллера
        """
        data = {"setting": setting, "values": values}
        return SettingsResponse(**self._request('POST', '/api/settings', data=data))

    def switch_output(self, index: int, level: bool) -> SwitchResponse:
        """Переключение цифрового выхода"""
        data = {"mode": SwitchMode.OUTPUTS, "index": index, "level": level}
        return SwitchResponse(**self._request('POST', '/api/switch', data=data))

    def switch_opencollectors(self, index: int, level: bool) -> SwitchResponse:
        """Переключение выхода открытого коллектора"""
        data = {"mode": SwitchMode.OPENCOLLECTORS, "index": index, "level": level}
        return SwitchResponse(**self._request('POST', '/api/switch', data=data))

    def scan_wifi(self) -> WiFiScanResponse:
        """Сканирование доступных WiFi сетей"""
        return WiFiScanResponse(**self._request('POST', '/api/wifi/scan'))

    def beep(self, count: int = 1, on_ms: int = 200, off_ms: int = 200) -> BeepResponse:
        """Включение пищалки"""
        data = {"count": max(1, count), "on_ms": min(1000, max(0, on_ms)), "off_ms": min(1000, max(0, off_ms))}
        return BeepResponse(**self._request('POST', '/api/beep', data=data))

    def save_full_configuration(self, config: Dict[str, Any]) -> ConfigurationResponse:
        """Сохранение полной конфигурации устройства"""
        return ConfigurationResponse(**self._request('POST', '/api/configuration', data=config))

    def create_automation(self, if_condition: Dict[str, Any], then_actions: List[Dict[str, Any]],
                          else_actions: Optional[List[Dict[str, Any]]] = None) -> AutomationCreateResponse:
        """Создание автоматизации"""
        data = {"if": if_condition, "then": then_actions}
        if else_actions:
            data["else"] = else_actions
        return AutomationCreateResponse(**self._request('POST', '/api/automations', data=data))

    # ============ PUT Methods ============

    def update_automation(self, automation_id: int, if_condition: Dict[str, Any],
                          then_actions: List[Dict[str, Any]],
                          else_actions: Optional[List[Dict[str, Any]]] = None) -> AutomationUpdateResponse:
        """Обновление автоматизации"""
        data = {"if": if_condition, "then": then_actions}
        if else_actions:
            data["else"] = else_actions
        return AutomationUpdateResponse(**self._request('PUT', f'/api/automations/{automation_id}', data=data))

    # ============ DELETE Methods ============

    def delete_automation(self, automation_id: int) -> AutomationDeleteResponse:
        """Удаление автоматизации"""
        return AutomationDeleteResponse(**self._request('DELETE', f'/api/automations/{automation_id}'))

    # ============ Convenience Methods ============

    def configure_mqtt(self, enabled: bool, host: str, port: int,
                       username: Optional[str] = None, password: Optional[str] = None) -> SettingsResponse:
        """Настройка MQTT"""
        values = {"en": enabled, "host": host, "port": port}
        if username is not None:
            values["user"] = username
        if password is not None:
            values["password"] = password
        return self.update_settings('mqtt', values)

    def configure_webhook(self, enabled: bool, url: str) -> SettingsResponse:
        """Настройка Webhook"""
        values = {"en": enabled, "url": url}
        return self.update_settings('webhook', values)

    def configure_ntc(self, channel: int, active: bool, label: str, offset: float = 0.0) -> SettingsResponse:
        """Настройка NTC датчика"""
        values = {"channel": channel, "active": active, "offset": offset, "label": label}
        return self.update_settings('ntc', values)

    def configure_adc(self, channel: int, active: bool, label: str, offset: float = 0.0) -> SettingsResponse:
        """Настройка ADC канала"""
        values = {"channel": channel, "active": active, "offset": offset, "label": label}
        return self.update_settings('adc', values)

    def configure_onewire(self, serial: str, label: str, active: bool, calibration: float = 0.0) -> SettingsResponse:
        """Настройка OneWire датчика"""
        values = {"serial": serial, "label": label, "active": active, "calibration": calibration}
        return self.update_settings('onewire', values)

    def configure_rf433(self, serial: int, label: str, alarm: bool,
                        device_type: int, mode: Optional[str] = None) -> SettingsResponse:
        """Настройка RF433 устройства"""
        values = {"serial": serial, "label": label, "alaram": alarm, "type": device_type}
        if mode:
            values["mode"] = mode
        return self.update_settings('rf433', values)

    def configure_opentherm(self, **kwargs) -> SettingsResponse:
        """Настройка OPENTHERM"""
        allowed_params = {'en', 'ch_en', 'ch_sp', 'dhw_en', 'dhw_sp', 'ch2_en', 'cool_en', 'mod', 'otc_en'}
        values = {k: v for k, v in kwargs.items() if k in allowed_params}
        return self.update_settings('opentherm', values)

    def configure_dio_output(self, index: int, enabled: bool, label: Optional[str] = None,
                             default_state: int = 0) -> SettingsResponse:
        """Настройка цифрового выхода"""
        values = {"en": enabled, "index": index, "default_state": default_state}
        if label:
            values["label"] = label
        return self.update_settings('outputs', values)

    def configure_dio_input(self, index: int, enabled: bool, label: Optional[str] = None) -> SettingsResponse:
        """Настройка цифрового входа"""
        values = {"en": enabled, "index": index}
        if label:
            values["label"] = label
        return self.update_settings('inputs', values)

    def check_connection(self) -> bool:
        """Проверка соединения с контроллером"""
        try:
            result = self.get_system_info()
            return result.success
        except Exception:
            return False


# ============ Example Usage ============

if __name__ == "__main__":
    controller = DeviceRestCommands("192.168.88.122")

    if controller.check_connection():
        print("Контроллер доступен")

        # Получаем системную информацию с типизированным ответом
        sys_info = controller.get_system_info()
        if sys_info.success and sys_info.data:
            print(f"Hostname: {sys_info.data.hostname}")
            print(f"Capabilities: {[cap.value for cap in sys_info.data.capabilities]}")
            print(f"Heap free: {sys_info.data.heap.free} bytes")

        # Получаем DIO информацию
        dio_info = controller.get_dio_info()
        if dio_info.success and dio_info.data:
            print(f"Inputs count: {len(dio_info.data.inputs)}")
            print(f"Outputs count: {len(dio_info.data.outputs)}")

        # Получаем конфигурацию
        config = controller.get_configuration('ntc')
        if config.success and config.data:
            print(f"NTC конфигурация: {config.data.model_dump_json(indent=2)}")

        # Сканируем WiFi
        wifi_scan = controller.scan_wifi()
        if wifi_scan.success and wifi_scan.data:
            for network in wifi_scan.data:
                print(f"SSID: {network.ssid}, RSSI: {network.rssi} dBm")

        # Получаем состояние
        state = controller.get_state('ntc1')
        if state.success and state.data:
            print(f"NTC1 значение: {state.data.state.value}")
            print(f"История: {state.data.history.count} записей")
    else:
        print("Контроллер недоступен")
