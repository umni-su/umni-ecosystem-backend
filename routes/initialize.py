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

from fastapi import APIRouter, Depends

from config.dependencies import get_ecosystem
from responses.init import InitResponse

initialize = APIRouter(
    prefix='/init',
    tags=['init']
)


@initialize.get('', response_model=InitResponse)
def init(
        ecosystem=Depends(get_ecosystem)
):
    success = ecosystem.installed
    return InitResponse(success=success)
