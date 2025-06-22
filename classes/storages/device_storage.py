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
        img = cv2.imread(os.path.abspath(ent.photo), cv2.IMREAD_UNCHANGED)
        h, w, channels = img.shape
        scale = width / w
        resized = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        success, im = cv2.imencode('.jpg', resized)
        headers = {'Content-Disposition': f'inline; filename="{ent.id}.jpg"'}
        return Response(im.tobytes(), headers=headers, media_type='image/jpeg')

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
