import os
from typing import Union

import cv2
from fastapi import UploadFile
from fastapi.responses import Response
from classes.storages.storage import StorageBase
from entities.device import Device
from entities.sensor import Sensor


class DeviceStorage(StorageBase):

    @classmethod
    def get_cover(cls, ent: Union[Device | Sensor], width: int):
        return cls.image_response(os.path.abspath(ent.photo), width)

    @classmethod
    def cover_response(cls, device: Device, width: int):
        return cls.get_cover(device, width)

    @classmethod
    def sensor_cover_response(cls, sensor: Sensor, width: int):
        return cls.get_cover(sensor, width)

    @classmethod
    def cover_upload(cls, device: Device, file: UploadFile):
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
