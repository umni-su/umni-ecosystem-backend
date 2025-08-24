import os
from typing import Union

from fastapi import UploadFile
from classes.storages.storage import StorageBase
from entities.device import DeviceEntity
from entities.sensor import Sensor


class DeviceStorage(StorageBase):

    @classmethod
    def get_cover(cls, ent: Union[DeviceEntity | Sensor], width: int):
        path = ent.photo
        if path is None:
            path = 'static/images/no-image.jpg'
        return cls.image_response(os.path.abspath(path), width)

    @classmethod
    def cover_response(cls, device: DeviceEntity, width: int):
        return cls.get_cover(device, width)

    @classmethod
    def sensor_cover_response(cls, sensor: Sensor, width: int):
        return cls.get_cover(sensor, width)

    @classmethod
    def cover_upload(cls, device: DeviceEntity, file: UploadFile):
        return cls.upload_file(
            folder=str(device.id),
            file=file,
            as_name='cover'
        )

    @classmethod
    def sensor_cover_upload(cls, sensor: Sensor, file: UploadFile):
        path = os.path.join(
            str(sensor.device.id),
            'sensors',
            str(sensor.id)
        )
        return cls.upload_file(
            folder=path,
            file=file,
            as_name='cover'
        )


device_storage = DeviceStorage('devices')
