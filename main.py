from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from starlette.websockets import WebSocket

from classes.logger import Logger
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


# fastapi dev .\main.py


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.create_all()
    ecosystem = Ecosystem()
    Logger.info('Generator lifespan at start of app')
    yield
    # Clean up the ML entities and release the resources
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


# @app.middleware("http")
# async def add_process_time_header(request: Request, call_next):
#     start_time = time.perf_counter()
#     response = await call_next(request)
#     process_time = time.perf_counter() - start_time
#     response.headers["X-Process-Time"] = str(process_time)
#     return response


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message text was: {data}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
