from contextlib import asynccontextmanager
from typing import Annotated

import uvicorn
from fastapi import FastAPI, Depends
from starlette.websockets import WebSocket

from classes.auth.auth import Auth
from classes.logger import Logger
from entities.user import UserEntity
from responses.user import UserResponseOut
from routes.cameras import cameras
from routes.storages import storages
from routes.auth import auth
from routes.devices import devices
from routes.install import install
from routes.initialize import initialize
from routes.configuration import conf

import database.database as db

from config.configuration import configuration
from classes.ecosystem import Ecosystem
from routes.sensors import sensors
from routes.systeminfo import systeminfo
from routes.websockets import websockets
from services.cameras.cameras_service import CamerasService


# fastapi dev .\main.py


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.create_all()
    ecosystem = Ecosystem()
    Logger.info('Generator lifespan at start of app')
    yield
    # Clean up the ML entities and release the resources
    for stream in CamerasService.streams:
        stream.opened = False
        stream.destroy_writer()
        Logger.warn(f'Force stop camera {stream.camera.name} stream')
    Logger.info('Finish lifespan at end of app')


app = FastAPI(
    lifespan=lifespan,
    root_path=configuration.api_root
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
app.include_router(websockets)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
