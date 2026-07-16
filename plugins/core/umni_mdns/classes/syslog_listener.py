import socket
import threading
import json
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass
import time

from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType


@dataclass
class SyslogMessage:
    """Класс для хранения полученного syslog сообщения"""
    timestamp: datetime
    source_host: str
    source_port: int
    raw_message: str
    message_type: str  # USER.INFO, USER.ERR и т.д.
    device_name: str  # umni-8389b4
    topic: str  # onewire, ntc, ai, outputs
    data: Dict[str, Any]  # распарсенный JSON


class SyslogListener:
    """Простой syslog слушатель на UDP"""

    def __init__(self, host: str = '0.0.0.0', port: int = 514):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.thread = None
        self.handlers = []

    def start(self):
        """Запуск слушателя"""
        if self.running:
            Logger.debug("The Syslog listener is already running", LoggerType.PLUGINS)
            return

        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.running = True

            self.thread = threading.Thread(target=self._listen, daemon=True)
            self.thread.start()

            Logger.debug(f"The Syslog listener is running on {self.host}:{self.port}", LoggerType.PLUGINS)
        except Exception as e:
            Logger.err(f" Launch error: {e}", LoggerType.PLUGINS)

    def stop(self):
        """Остановка слушателя"""
        if not self.running:
            Logger.debug("The Syslog listener has already been stopped", LoggerType.PLUGINS)
            return

        self.running = False
        if self.socket:
            self.socket.close()
            self.socket = None

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1)

        Logger.debug("Syslog listener stopped", LoggerType.PLUGINS)

    def restart(self):
        """Перезапуск слушателя"""
        Logger.debug("Restarting the syslog listener...", LoggerType.PLUGINS)
        self.stop()
        time.sleep(0.5)
        self.start()

    def add_handler(self, handler_func):
        """Добавление обработчика для сообщений"""
        self.handlers.append(handler_func)

    def _parse_message(self, data: bytes, addr: tuple) -> Optional[SyslogMessage]:
        """Парсинг syslog сообщения"""
        try:
            raw = data.decode('utf-8', errors='ignore').strip()

            validated = self._validate_message(raw)
            if not validated:
                return None

            device, topic, json_str = validated
            data_dict = json.loads(json_str)

            return SyslogMessage(
                timestamp=datetime.now(),
                source_host=addr[0],
                source_port=addr[1],
                raw_message=raw,
                message_type="USER.INFO",
                device_name=device,
                topic=topic,
                data=data_dict
            )

        except Exception:
            return None

    def _validate_message(self, raw: str) -> Optional[tuple]:
        """
        Валидация сообщения.
        Возвращает (device, topic, json_str) или None
        """
        try:
            # Убираем syslog префикс типа <14> если есть
            if raw.startswith('<') and '>' in raw:
                raw = raw.split('>', 1)[1]

            # Проверяем, что начинается с umni-
            if not raw.startswith('umni-'):
                return None

            # Разделяем на часть до JSON и сам JSON
            if ': ' not in raw:
                return None

            parts = raw.split(': ', 1)
            if len(parts) < 2:
                return None

            device_and_topic = parts[0]
            json_str = parts[1]

            # Разделяем устройство и тему
            dt_parts = device_and_topic.split(' ', 1)
            if len(dt_parts) < 2:
                return None

            device = dt_parts[0]
            topic = dt_parts[1]

            # Проверяем JSON
            json.loads(json_str)

            return device, topic, json_str

        except (json.JSONDecodeError, ValueError, IndexError):
            return None

    def _dispatch_message(self, message: SyslogMessage):
        """Отправка сообщения всем обработчикам"""
        for handler in self.handlers:
            try:
                handler(message)
            except Exception as e:
                Logger.err(f"Error in the handler: {e}", LoggerType.PLUGINS)

    def _listen(self):
        """Основной цикл прослушивания"""
        Logger.debug("We start listening to syslog messages...", LoggerType.PLUGINS)

        while self.running:
            try:
                self.socket.settimeout(0.5)
                data, addr = self.socket.recvfrom(4096)

                message = self._parse_message(data, addr)
                if message:
                    self._dispatch_message(message)

            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    Logger.err(f"Receive error: {e}", LoggerType.PLUGINS)

    def get_status(self) -> dict:
        """Получение статуса слушателя"""
        return {
            'running': self.running,
            'host': self.host,
            'port': self.port,
            'handlers_count': len(self.handlers)
        }

# ========== Пример использования ==========
#
# def main():
#     # Создаем слушатель
#     listener = SyslogListener(host='0.0.0.0', port=514)
#
#     # Пример обработчика - просто выводит сообщение
#     def print_handler(msg: SyslogMessage):
#         print(f"[{msg.timestamp.strftime('%H:%M:%S')}] "
#               f"{msg.source_host}:{msg.source_port} "
#               f"{msg.device_name} [{msg.topic}] "
#               f"data: {msg.data}")
#
#     # Добавляем обработчик
#     listener.add_handler(print_handler)
#
#     # Запускаем
#     listener.start()
#
#     # Проверяем статус
#     print(f"Статус: {listener.get_status()}")
#
#     try:
#         # Держим программу запущенной
#         while True:
#             time.sleep(1)
#
#             # Пример проверки состояния
#             if not listener.get_status()['running']:
#                 print("⚠️ Слушатель остановлен, перезапускаем...")
#                 listener.restart()
#
#     except KeyboardInterrupt:
#         print("\n👋 Получен сигнал остановки")
#     finally:
#         listener.stop()
#
#
# if __name__ == "__main__":
#     main()
