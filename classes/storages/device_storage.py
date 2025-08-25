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
