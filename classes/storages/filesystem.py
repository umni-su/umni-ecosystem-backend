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
