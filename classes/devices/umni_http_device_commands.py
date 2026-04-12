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
from typing import Optional, Dict, Any


class UmniHttpDeviceCommands:
    def __init__(self, ip_address: str, timeout: int = 10):
        """
        Инициализация клиента

        :param ip_address: IP адрес контроллера
        :param timeout: Таймаут запроса в секундах
        """
        self.ip = ip_address
        self.timeout = timeout
        self.base_url = f"http://{ip_address}"

    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Внутренний метод для выполнения запросов

        :param method: HTTP метод (GET, POST)
        :param endpoint: Путь API (например '/api/systeminfo')
        :param data: Данные для отправки (для POST запросов)
        :return: Ответ от API в виде словаря
        """
        url = f"{self.base_url}{endpoint}"

        headers = {
            'Content-Type': 'application/json'
        }

        if data is not None:
            json_data = json.dumps(data).encode('utf-8')
            req = urllib.request.Request(url, data=json_data, headers=headers, method=method)
        else:
            req = urllib.request.Request(url, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                response_data = response.read().decode('utf-8')
                return json.loads(response_data)
        except urllib.error.URLError as e:
            raise Exception(f"Ошибка соединения с контроллером {self.ip}: {e}")
        except json.JSONDecodeError as e:
            raise Exception(f"Ошибка парсинга JSON ответа: {e}")

    def get_system_info(self) -> Dict[str, Any]:
        """
        Получение системной информации

        :return: Информация о системе
        """
        return self._request('GET', '/api/systeminfo')

    def get_dio_info(self) -> Dict[str, Any]:
        """
        Получение информации о цифровых входах/выходах

        :return: Информация о DIO
        """
        return self._request('GET', '/api/dio')

    def get_adc_info(self) -> Dict[str, Any]:
        """
        Получение информации об аналоговых входах

        :return: Информация об ADC
        """
        return self._request('GET', '/api/adc')

    def get_ntc_info(self) -> Dict[str, Any]:
        """
        Получение информации о NTC датчиках

        :return: Информация о NTC
        """
        return self._request('GET', '/api/ntc')

    def get_onewire_info(self) -> Dict[str, Any]:
        """
        Получение информации о OneWire датчиках

        :return: Информация о OneWire
        """
        return self._request('GET', '/api/onewire')

    def get_rf433_info(self) -> Dict[str, Any]:
        """
        Получение информации об RF433 устройствах

        :return: Информация о RF433
        """
        return self._request('GET', '/api/rf433')

    def get_opentherm_info(self) -> Dict[str, Any]:
        """
        Получение информации о состоянии Opentherm

        :return: Информация об Opentherm
        """
        return self._request('GET', '/api/opentherm')

    def update_settings(self, setting: str, values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обновление настроек контроллера

        :param setting: Ключ настройки (например 'mqtt', 'webhook', 'outputs')
        :param values: Значения настройки
        :return: Ответ от API
        """
        data = {
            "setting": setting,
            "values": values
        }
        return self._request('POST', '/api/settings', data)

    def switch_output(self, index: int, state: int) -> Dict[str, Any]:
        """
        Переключение выхода

        :param index: Индекс выхода (начинается с 1)
        :param state: Состояние (0 - выключить, 1 - включить)
        :return: Ответ от API
        """
        data = {
            "index": index,
            "state": state
        }
        return self._request('POST', '/api/switch', data)

    def configure_mqtt(self, enabled: bool, host: str, port: int,
                       username: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
        """
        Настройка MQTT

        :param enabled: Включить/выключить MQTT
        :param host: Адрес MQTT брокера
        :param port: Порт MQTT брокера
        :param username: Имя пользователя (опционально)
        :param password: Пароль (опционально)
        :return: Ответ от API
        """
        values = {
            "en": enabled,
            "host": host,
            "port": port
        }
        if username is not None:
            values["user"] = username
        if password is not None:
            values["password"] = password

        return self.update_settings('mqtt', values)

    def configure_webhook(self, enabled: bool, url: str) -> Dict[str, Any]:
        """
        Настройка Webhook

        :param enabled: Включить/выключить Webhook
        :param url: URL для отправки данных
        :return: Ответ от API
        """
        values = {
            "en": enabled,
            "url": url
        }
        return self.update_settings('webhook', values)

    def configure_ntc(self, channel: int, active: bool, label: str,
                      offset: float = 0.0) -> Dict[str, Any]:
        """
        Настройка NTC датчика

        :param channel: Номер канала (0 или 1)
        :param active: Активен ли датчик
        :param label: Метка датчика
        :param offset: Корректировка показаний
        :return: Ответ от API
        """
        values = {
            "channel": channel,
            "active": active,
            "offset": offset,
            "label": label
        }
        return self.update_settings('ntc', values)

    def check_connection(self) -> bool:
        """
        Проверка соединения с контроллером

        :return: True если контроллер доступен
        """
        try:
            result = self.get_system_info()
            return result.get('success', False)
        except Exception:
            return False

# Пример использования
# if __name__ == "__main__":
#     # Создаем клиент для работы с контроллером
#     controller = UmniHttpDeviceCommands("192.168.88.122")
#
#     # Проверяем соединение
#     if controller.check_connection():
#         print("Контроллер доступен")
#
#         # Получаем системную информацию
#         sys_info = controller.get_system_info()
#         print(f"Системная информация: {json.dumps(sys_info, indent=2, ensure_ascii=False)}")
#
#         # Получаем информацию о DIO
#         dio_info = controller.get_dio_info()
#         print(f"DIO информация: {json.dumps(dio_info, indent=2, ensure_ascii=False)}")
#
#         # Пример переключения выхода №1
#         # result = controller.switch_output(1, 1)
#         # print(f"Результат переключения: {result}")
#
#         # Пример настройки MQTT
#         # result = controller.configure_mqtt(
#         #     enabled=True,
#         #     host="mqtt.example.com",
#         #     port=1883,
#         #     username="user",
#         #     password="pass"
#         # )
#         # print(f"Результат настройки MQTT: {result}")
#     else:
#         print("Контроллер недоступен")
