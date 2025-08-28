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

import os.path
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from classes.storages.filesystem import Filesystem
from fastapi import UploadFile, Response
import cv2


class StorageBase:
    path: str | None = None

    def __init__(self, path: str):
        root = os.path.abspath('./storage')
        StorageBase.path = os.path.join(root, os.path.normpath(path))
        Logger.debug(f'Init storage {StorageBase.path}', LoggerType.STORAGES)
        if not StorageBase.exists(StorageBase.path):
            Filesystem.mkdir(StorageBase.path)

    @classmethod
    def upload_file(cls, folder: str, file: UploadFile, as_name: str | None = None):
        join_path = os.path.join(
            cls.path,
            folder
        )
        try:
            dir_exists = Filesystem.exists(join_path)
            if not dir_exists:
                Filesystem.mkdir(join_path)

            if isinstance(as_name, str):
                filename, extension = os.path.splitext(file.filename)
                join_path = os.path.join(join_path, ''.join([
                    as_name,
                    extension
                ]))
            else:
                join_path = os.path.join(join_path, file.filename)

            contents = file.file.read()
            with open(join_path, 'wb') as f:
                f.write(contents)
                return os.path.relpath(join_path)
        except Exception as e:
            Logger.err(f"Error uploading file {join_path}", LoggerType.STORAGES)
            raise e
        finally:
            file.file.close()

    @classmethod
    def get_path(cls, path):
        if not os.path.isabs(path):
            path = os.path.abspath(path)
        return path

    @classmethod
    def remove(cls, path: str):
        path = cls.get_path(path)
        if Filesystem.exists(path):
            os.unlink(path)

    @classmethod
    def exists(cls, path: str):
        return Filesystem.exists(path)

    @classmethod
    def image_response(cls, path: str, width: int = 200):
        img = cv2.imread(os.path.abspath(path), cv2.IMREAD_UNCHANGED)
        name = os.path.basename(path)
        h, w, channels = img.shape
        scale = width / w
        resized = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        success, im = cv2.imencode('.jpg', resized)
        headers = {'Content-Disposition': f'inline; filename="{name}"'}
        return Response(im.tobytes(), headers=headers, media_type='image/jpeg')
