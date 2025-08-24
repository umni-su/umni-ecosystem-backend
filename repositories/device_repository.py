from fastapi import UploadFile
from sqlmodel import select, col

from classes.logger import Logger
from classes.storages.device_storage import device_storage
from classes.storages.upload_validator import UploadValidator
from database.session import write_session
from entities.device import DeviceEntity
from models.device_model import DeviceUpdateModel, DeviceModelWithRelations
from repositories.base_repository import BaseRepository


class DeviceRepository(BaseRepository):
    @classmethod
    def get_devices(cls):
        with write_session() as sess:
            devices_orm = sess.exec(
                select(DeviceEntity).order_by(
                    col(DeviceEntity.id).desc()
                )
            ).all()
            return [
                DeviceModelWithRelations.model_validate(
                    _d.to_dict(
                        include_relationships=True
                    )
                ) for _d in devices_orm
            ]

    @classmethod
    def get_device(cls, device_id: int):
        with write_session() as sess:
            device_orm = sess.exec(
                select(DeviceEntity).where(DeviceEntity.id == device_id)
            ).first()
            return DeviceModelWithRelations.model_validate(
                device_orm.to_dict(
                    include_relationships=True
                )
            )

    @classmethod
    def update_device(cls, device_id: int, model: DeviceUpdateModel):
        with write_session() as sess:
            device = sess.get(DeviceEntity, device_id)
            device.title = model.title
            sess.add(device)
            sess.commit()
            sess.refresh(device)

            return DeviceModelWithRelations.model_validate(
                device.to_dict(
                    include_relationships=True
                )
            )

    @classmethod
    def upload_device_cover(cls, device_id: int, cover: UploadFile):
        with write_session() as sess:
            try:
                device = sess.get(DeviceEntity, device_id)
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

                return DeviceModelWithRelations.model_validate(
                    device.to_dict(
                        include_relationships=True
                    )
                )

            except Exception as e:
                Logger.err(e)
