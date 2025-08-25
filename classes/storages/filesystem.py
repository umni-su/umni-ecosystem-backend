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


class Filesystem:
    @staticmethod
    def mkdir(path_or_filename: str, mode: int = 0o777, recursive: bool = True, exist=True):
        path = Path(path_or_filename)
        path.mkdir(mode, recursive, exist)

    @staticmethod
    def exists(path: str) -> bool:
        if not os.path.isabs(path):
            path = os.path.abspath(path)
        return os.path.exists(path)

    '''
    https://stackoverflow.com/questions/1392413/calculating-a-directorys-size-using-python
    return bytes
    '''

    @staticmethod
    def get_size(start_path: str | None = '.'):
        total_size = 0
        if start_path is None:
            return total_size
        for dirpath, dirnames, filenames in os.walk(start_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                # skip if it is symbolic link
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
        return total_size
