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

import uvicorn
from fastapi import FastAPI

from classes.app.lifespan_manager import lifespan_manager
from routes.access import access
from routes.cameras import cameras
from routes.events import events
from routes.logs import logs
from routes.plugins import plugins
from routes.storages import storages
from routes.auth import auth
from routes.devices import devices
from routes.install import install
from routes.initialize import initialize
from routes.configuration import conf
from routes.rules import rules
from routes.sensors import sensors
from routes.systeminfo import systeminfo
from routes.users import users
from routes.websockets import websockets
from routes.notifications import notifications
from config.settings import settings

from services.cameras.classes.stream_registry import StreamRegistry

app = FastAPI(
    lifespan=lifespan_manager.lifespan,
    root_path=settings.API_ROOT
)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "shutting_down": lifespan_manager.is_shutting_down,
        "stream_state": StreamRegistry.get_state().value
    }


# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=['*'],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
app.include_router(access)
app.include_router(auth)
app.include_router(cameras)
app.include_router(conf)
app.include_router(devices)
app.include_router(events)
app.include_router(initialize)
app.include_router(install)
app.include_router(logs)
app.include_router(notifications)
app.include_router(rules)
app.include_router(plugins)
app.include_router(sensors)
app.include_router(storages)
app.include_router(systeminfo)
app.include_router(users)
app.include_router(websockets)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
