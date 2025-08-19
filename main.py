import time
from contextlib import asynccontextmanager

from classes.ecosystem import Ecosystem
from classes.logger import Logger

import uvicorn
from fastapi import FastAPI

from database.database import db_manager
from database.migrations import MigrationManager

from routes.cameras import cameras
from routes.events import events
from routes.storages import storages
from routes.auth import auth
from routes.devices import devices
from routes.install import install
from routes.initialize import initialize
from routes.configuration import conf
from routes.rules import rules

from config.settings import settings
from routes.sensors import sensors
from routes.systeminfo import systeminfo
from routes.websockets import websockets
from services.cameras.cameras_service import CamerasService


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Только если используем Nuitka (проверка скомпилированного режима)
    # if getattr(sys, 'frozen', False):
    MigrationManager.run_migrations()
    ecosystem = Ecosystem()
    Logger.info('Generator lifespan at start of app')
    yield
    # Clean up the ML entities and release the resources
    for stream in CamerasService.streams:
        stream.opened = False
        stream.destroy_output_container()
        Logger.warn(f'❌ {stream.camera.name} Force stop camera stream')
    Logger.info('Finish lifespan at end of app')


app = FastAPI(
    lifespan=lifespan,
    root_path=settings.API_ROOT
)
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=['*'],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
app.include_router(conf)
app.include_router(auth)
app.include_router(initialize)
app.include_router(install)
app.include_router(devices)
app.include_router(sensors)
app.include_router(storages)
app.include_router(systeminfo)
app.include_router(cameras)
app.include_router(events)
app.include_router(rules)
app.include_router(websockets)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
