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
import re

from config.settings import settings

# Windows-absolute путь: "D:\folder" или "D:/folder"
_WINDOWS_ABS = re.compile(r'^[A-Za-z]:[\\/](.*)$')


class PathMap:
    """Переводит хостовые пути хранилищ в пути, доступные внутри контейнера.

    Логика одинакова для Windows, Linux и Docker:
    - путь вида "D:\\CameraData" -> "<host_base>/D/CameraData", если он существует
      (Docker с примонтированным диском); иначе путь возвращается как есть
      (Windows-native).
    - любой другой путь (Linux-absolute или относительный) не меняется.
    """

    def __init__(self, host_base: str = '/host'):
        self.host_base = (host_base or '').rstrip('/\\')

    def resolve(self, path: str | None) -> str | None:
        if not path or not self.host_base:
            return path
        match = _WINDOWS_ABS.match(path)
        if not match:
            return path
        drive = path[0].upper()
        rest = match.group(1).replace('\\', '/')
        mapped = f'{self.host_base}/{drive}/{rest}'
        if os.path.exists(mapped):
            return mapped
        return path


path_map = PathMap(settings.STORAGE_HOST_BASE)
