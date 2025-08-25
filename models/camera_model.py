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

from pydantic import BaseModel, Field, computed_field

from entities.enums.camera_protocol_enum import CameraProtocolEnum
from entities.enums.camera_record_type_enum import CameraRecordTypeEnum
from models.camera_area_model import CameraAreaBaseModel
from models.storage_model import StorageModel


class CameraGetModel(BaseModel):
    id: int | None = None
    storage_id: int
    name: str


class CameraBaseModel(CameraGetModel):
    active: bool = True
    alerts: bool = True
    record: bool = False
    record_duration: int | None = None
    record_mode: CameraRecordTypeEnum | None = None
    delete_after: int | None = None
    cover: str | None = None
    protocol: CameraProtocolEnum
    ip: str | None = None
    port: int | None = None
    username: str | None = None
    password: str | None = Field(exclude=True, default=None)
    primary: str | None = None
    secondary: str | None = None
    change_credentials: bool = False

    @computed_field
    @property
    def has_credentials(self) -> bool:
        return True if (self.password is not None or self.username is not None) else False


class CameraModelWithRelations(CameraBaseModel):
    # location:
    storage: StorageModel | None = None
    areas: list[CameraAreaBaseModel] | None = None
