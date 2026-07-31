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
import asyncio
import os
import sys
from typing import Annotated

from fastapi import APIRouter, Depends

from classes.auth.auth import Auth
from responses.success import SuccessResponse
from responses.user import UserResponseOut

settings = APIRouter(
    prefix="/settings",
    tags=["settings"]
)


@settings.post("/restart")
async def restart():
    async def shutdown():
        await asyncio.sleep(1)
        os._exit(0)  # Служба закроется, а Windows (благодаря настройке sc failure) сразу её поднимет

    asyncio.create_task(shutdown())
    return {"success": True}
