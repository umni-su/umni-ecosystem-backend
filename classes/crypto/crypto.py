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

        if key is not None:
            Logger.info(f"Encryption key loaded from environment variable {cls._key_env_var}", LoggerType.APP)
            return key

        return cls._generate_and_save_key_to_env()

    @classmethod
    def create_key(cls) -> str:
        return cls._generate_and_save_key_to_env()

    @classmethod
    def _generate_and_save_key_to_env(cls, force: bool = False) -> str:
        if settings.ENCRYPTION_KEY is None or settings.ENCRYPTION_KEY == '' or force:

            """Генерирует новый ключ и добавляет в .env файл"""
            new_key = Fernet.generate_key().hex()

            # Добавляем ключ в .env файл
            env_path = Path('./env_config/.env').resolve()

            try:
                # Если файла вообще нет, создаем его пустым, чтобы r+ сработал
                if not env_path.exists():
                    env_path.touch()

                # Открываем файл в режиме r+ (чтение и запись без удаления/пересоздания inode)
                with open(env_path, 'r+', encoding='utf-8') as f:
                    lines = f.readlines()

                    # Проверяем, есть ли уже ENCRYPTION_KEY
                    key_found = False
                    for i, line in enumerate(lines):
                        if line.startswith('ENCRYPTION_KEY='):
                            lines[i] = f'ENCRYPTION_KEY={new_key}\n'
                            key_found = True
                            break

                    # Если нет - добавляем в конец
                    if not key_found:
                        if lines and not lines[-1].endswith('\n'):
                            lines.append('\n')  # Перенос строки, если его не было
                        lines.append(f'ENCRYPTION_KEY={new_key}\n')

                    # Сбрасываем указатель в начало файла
                    f.seek(0)
                    # Записываем обновленные строки поверх старых
                    f.writelines(lines)
                    # Обрезаем остатки старого контента, если новый файл стал меньше
                    f.truncate()

                    # Принудительно заставляем Docker и ОС синхронизировать файл с хостом
                    f.flush()
                    os.fsync(f.fileno())

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
            # cls._generate_and_save_key_to_env(force=True)
            Logger.err(f"Decryption error, {e}", LoggerType.APP, with_db=True)
            # Logger.err(f"Decryption error, generate new key force: {e}", LoggerType.APP, with_db=True)

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
