import os
import cv2
from fastapi import UploadFile
from fastapi.responses import Response
from classes.storages.storage import StorageBase
from entities.device import Device


class DeviceStorage(StorageBase):
    @classmethod
    def cover_response(cls, device: Device, width: int):
        img = cv2.imread(os.path.abspath(device.photo), cv2.IMREAD_UNCHANGED)
        h, w, channels = img.shape
        scale = width / w
        resized = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        success, im = cv2.imencode('.jpg', resized)
        headers = {'Content-Disposition': f'inline; filename="{device.id}.jpg"'}
        return Response(im.tobytes(), headers=headers, media_type='image/jpeg')

    @classmethod
    def cover_upload(cls, device: Device, file: UploadFile):
        return cls.upload_file(
            folder=str(device.id),
            file=file,
            as_name='cover'
        )


device_storage = DeviceStorage('devices')
