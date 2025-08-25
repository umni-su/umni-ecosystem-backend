import uvicorn
from fastapi import FastAPI

from classes.app.lifespan_manager import lifespan_manager
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
