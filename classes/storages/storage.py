import os.path
from classes.logger import logger
from classes.storages.filesystem import Filesystem
from fastapi import UploadFile


class StorageBase:
    path: str | None = None

    def __init__(self, path: str):
        root = os.path.abspath('./storage')
        StorageBase.path = os.path.join(root, os.path.normpath(path))
        logger.debug(f'Init storage {StorageBase.path}')
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
            logger.err(f"Error uploading file {join_path}")
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
