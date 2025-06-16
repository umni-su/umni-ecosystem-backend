import os.path
from pathlib import Path


class Filesystem:
    @staticmethod
    def mkdir(path_or_filename: str, mode: int = 0o777, recursive: bool = True, exist=True):
        path = Path(path_or_filename)
        path.mkdir(mode, recursive, exist)

    @staticmethod
    def exists(path: str) -> bool:
        return Path(path).exists()
