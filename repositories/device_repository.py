from fastapi import UploadFile
from sqlmodel import select, col

from classes.logger import logger
from classes.storages.device_storage import device_storage
from classes.storages.upload_validator import UploadValidator
from database.database import session_scope
from entities.device import Device
from models.device_model import DeviceUpdateModel
from repositories.base_repository import BaseRepository


class DeviceRepository(BaseRepository):
    @classmethod
    def get_devices(cls):
        with session_scope() as sess:
            yield sess.exec(
                select(Device).order_by(
                    col(Device.id).desc()
                )
            ).all()

    @classmethod
    def get_device(cls, device_id: int):
        with session_scope() as sess:
            yield sess.exec(
                select(Device).where(Device.id == device_id)
            ).first()

    @classmethod
    def update_device(cls, device_id: int, model: DeviceUpdateModel):
        with session_scope() as sess:
            device = next(cls.get_device(device_id))
            device.title = model.title
            sess.add(device)
            sess.commit()
            sess.refresh(device)
            yield device

    @classmethod
    def upload_device_cover(cls, device_id: int, cover: UploadFile):
        with session_scope() as sess:
            try:
                device = next(cls.get_device(device_id))
                photo = device_storage.cover_upload(
                    device=device,
                    file=cover
                )
                device.photo = photo
                sess.add(device)
                validator = UploadValidator(cover)
                validator.is_image().max_size(5).validate()
                sess.add(device)
                sess.commit()
                sess.refresh(device)
                yield device
            except Exception as e:
                logger.error(e)
