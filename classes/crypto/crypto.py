# crypto.py
#  Copyright (C) 2025 Mikhail Sazanov
#  #
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#  #
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#  #
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
import os
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.fernet import Fernet
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from config.settings import settings


class Crypto:
    _fernet = None
    _key_env_var = 'ENCRYPTION_KEY'

    @classmethod
    def _get_key_from_env(cls) -> str:
        """Получает ключ из переменной окружения"""
        key = settings.ENCRYPTION_KEY

        if key:
            Logger.info(f"Encryption key loaded from environment variable {cls._key_env_var}", LoggerType.APP)
            return key

        # Проверяем файл (обратная совместимость)
        key_file = os.getenv(cls._key_env_var)
        if key_file and Path(key_file).exists():
            Logger.info(f"Encryption key loaded from file: {key_file}", LoggerType.APP)
            with open(key_file, 'r') as f:
                return f.read().strip()

        # Если ключа нет - генерируем и сохраняем
        return cls._generate_and_save_key_to_env()

    @classmethod
    def _generate_and_save_key_to_env(cls, force: bool = False) -> str:
        if settings.ENCRYPTION_KEY is None or force:
            """Генерирует новый ключ и добавляет в .env файл"""
            new_key = Fernet.generate_key().hex()

            # Добавляем ключ в .env файл
            env_path = Path('.env')

            try:
                # Читаем существующий .env
                if env_path.exists():
                    with open(env_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                else:
                    lines = []

                # Проверяем есть ли уже ENCRYPTION_KEY
                key_found = False
                for i, line in enumerate(lines):
                    if line.startswith('ENCRYPTION_KEY='):
                        lines[i] = f'ENCRYPTION_KEY={new_key}\n'
                        key_found = True
                        break

                # Если нет - добавляем в конец
                if not key_found:
                    lines.append(f'ENCRYPTION_KEY={new_key}\n')

                # Записываем обратно
                with open(env_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)

                Logger.info(f"Generated new encryption key and saved to .env file", LoggerType.APP)
                return new_key

            except Exception as e:
                Logger.err(f"Failed to save encryption key to .env: {e}", LoggerType.APP)
                raise
        return settings.ENCRYPTION_KEY

    @classmethod
    def _get_fernet(cls):
        if cls._fernet is None:
            key = cls._get_key_from_env()

            key = bytes.fromhex(key)

            cls._fernet = Fernet(key)
        return cls._fernet

    @classmethod
    def encrypt(cls, value: str) -> str | None:
        """Шифрует строку"""
        try:
            if value is None:
                return value
            return cls._get_fernet().encrypt(value.encode()).decode()
        except Exception as e:
            Logger.err(f"Encryption error: {e}", LoggerType.APP)
            raise

    @classmethod
    def decrypt(cls, encrypted_value: str) -> str | None:
        """Дешифрует строку"""
        try:
            if encrypted_value is None:
                return encrypted_value
            return cls._get_fernet().decrypt(encrypted_value.encode()).decode()
        except InvalidSignature as e:
            cls._generate_and_save_key_to_env(force=True)
            Logger.err(f"Decryption error, generate new key force: {e}", LoggerType.APP, with_db=True)
        except Exception as e:
            cls._generate_and_save_key_to_env(force=True)
            Logger.err(f"Decryption error, generate new key force: {e}", LoggerType.APP, with_db=True)

    @classmethod
    def get_key_string(cls):
        """Возвращает текущий ключ"""
        return cls._get_key_from_env()

    @classmethod
    def rotate_key(cls) -> bool:
        """Генерирует новый ключ и обновляет .env"""
        try:
            new_key = Fernet.generate_key().decode()

            env_path = Path('.env')
            if env_path.exists():
                with open(env_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                key_found = False
                for i, line in enumerate(lines):
                    if line.startswith('ENCRYPTION_KEY='):
                        lines[i] = f'ENCRYPTION_KEY={new_key}\n'
                        key_found = True
                        break

                if not key_found:
                    lines.append(f'ENCRYPTION_KEY={new_key}\n')

                with open(env_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)

            cls._fernet = None

            Logger.warn(
                f"Encryption key rotated! All previously encrypted data is now INACCESSIBLE!",
                LoggerType.APP
            )
            return True

        except Exception as e:
            Logger.err(f"Failed to rotate encryption key: {e}", LoggerType.APP)
            return False
