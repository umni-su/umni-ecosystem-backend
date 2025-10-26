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
import stat
from pathlib import Path
from cryptography.fernet import Fernet
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType


class Crypto:
    _fernet = None
    _key_file_path = None

    @classmethod
    def _get_key_file_path(cls) -> Path:
        """Получает путь к файлу с ключом из .env или использует default"""
        if cls._key_file_path is None:
            key_path = os.getenv('ENCRYPTION_KEY_FILE', '.ecosystem.key')
            cls._key_file_path = Path(key_path)
        return cls._key_file_path

    @classmethod
    def _ensure_secure_permissions(cls, file_path: Path):
        """Устанавливает безопасные права доступа на файл с ключом"""
        try:
            # Только владелец может читать/писать
            file_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
        except Exception as e:
            Logger.warn(f"Could not set secure permissions on {file_path}: {e}", LoggerType.APP)

    @classmethod
    def _generate_and_save_key(cls) -> str:
        """Генерирует новый ключ и сохраняет в файл"""
        key_file = cls._get_key_file_path()

        # Генерируем ключ
        new_key = Fernet.generate_key().decode()

        # Сохраняем в файл
        try:
            key_file.parent.mkdir(parents=True, exist_ok=True)
            with open(key_file, 'w') as f:
                f.write(new_key)

            # Устанавливаем безопасные права
            cls._ensure_secure_permissions(key_file)

            Logger.info(f"Generated new encryption key and saved to {key_file}", LoggerType.APP)
            return new_key

        except Exception as e:
            Logger.err(f"Failed to save encryption key to {key_file}: {e}", LoggerType.APP)
            raise

    @classmethod
    def _load_key_from_file(cls) -> str:
        """Загружает ключ из файла"""
        key_file = cls._get_key_file_path()

        try:
            with open(key_file, 'r') as f:
                key_content = f.read().strip()

            if not key_content:
                raise ValueError("Encryption key file is empty")

            return key_content

        except FileNotFoundError:
            # Файл не существует - создаем новый
            return cls._generate_and_save_key()
        except Exception as e:
            Logger.err(f"Failed to load encryption key from {key_file}: {e}", LoggerType.APP)
            raise

    @classmethod
    def _get_fernet(cls):
        if cls._fernet is None:
            # Загружаем ключ из файла
            encryption_key = cls._load_key_from_file()
            key = bytes.fromhex(encryption_key)
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
        except Exception as e:
            Logger.err(f"Decryption error: {e}", LoggerType.APP)
            raise

    @classmethod
    def get_key_string(cls):
        return cls._load_key_from_file()

    @classmethod
    def rotate_key(cls, new_key_file: Path = None) -> bool:
        """
        Генерирует новый ключ шифрования

        Args:
            new_key_file: Опционально новый путь для ключа

        Returns:
            bool: Успешно ли создан новый ключ

        Warning: Все зашифрованные данные станут нечитаемыми!
        """
        try:
            old_key_file = cls._get_key_file_path()

            # Генерируем новый ключ
            if new_key_file:
                cls._key_file_path = Path(new_key_file)
            new_key = cls._generate_and_save_key()

            Logger.warn(
                f"Encryption key rotated! Old key: {old_key_file}, New key: {cls._get_key_file_path()}. "
                f"All previously encrypted data is now INACCESSIBLE!",
                LoggerType.APP
            )

            # Сбрасываем кэш Fernet чтобы использовать новый ключ
            cls._fernet = None

            return True

        except Exception as e:
            Logger.err(f"Failed to rotate encryption key: {e}", LoggerType.APP)
            return False

    @classmethod
    def get_key_info(cls) -> dict:
        """Возвращает информацию о текущем ключе"""
        key_file = cls._get_key_file_path()
        exists = key_file.exists()

        info = {
            'key_file': str(key_file),
            'exists': exists,
            'absolute_path': str(key_file.absolute()),
        }

        if exists:
            try:
                stat_info = key_file.stat()
                info.update({
                    'file_size': stat_info.st_size,
                    'permissions': oct(stat_info.st_mode)[-3:],
                    'modified': stat_info.st_mtime,
                })
            except Exception as e:
                info['error'] = str(e)

        return info
