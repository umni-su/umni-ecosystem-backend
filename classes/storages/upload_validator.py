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

from enum import StrEnum

from fastapi import UploadFile, HTTPException, status

MAX_UPLOAD_SIZE = 20


class ImagesMimes(StrEnum):
    JPEG = 'image/jpeg'
    PNG = 'image/png'


class UploadValidator:
    file: UploadFile
    errors: [str] = []

    def __init__(self, file: UploadFile):
        self.file = file

    def is_mime(self):

        return self

    def is_image(self):
        res: bool = self.file.content_type in ImagesMimes
        if not res:
            self.errors.append('Wrong mime type')

        return self

    def max_size(self, max_mb: int | None = None):
        size = self.file.size / pow(1024, 2)
        if max_mb is None:
            max_mb = MAX_UPLOAD_SIZE
        if size >= MAX_UPLOAD_SIZE:
            self.errors.append(f'File must be less or equal {max_mb} MB')
        return self

    def has_errors(self):
        return len(self.errors) > 0

    def validate(self):
        if self.has_errors():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=self.errors,
            )
        self.errors = []
