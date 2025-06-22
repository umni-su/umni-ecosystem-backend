import os.path

from sqlmodel import SQLModel, create_engine, Session

from config.configuration import configuration
from classes.storages.filesystem import Filesystem

# IMPORT MODELS #

from entities.storage import StorageEntity
from entities.user import UserEntity
from entities.configuration import ConfigurationEntity
from entities.device import Device
from entities.sensor import Sensor
from entities.sensor_history import SensorHistory
from entities.device_network_interfaces import DeviceNetworkInterface

fn = os.path.join(configuration.db_dir, configuration.db_source)
filename = f"{fn}"
sqlite_url = f"sqlite:///{filename}"
if not Filesystem.exists(filename):
    Filesystem.mkdir(configuration.db_dir)
connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)
session = Session(engine)


def create_all():
    SQLModel.metadata.create_all(engine)


def get_session():
    return session


def get_separate_session():
    return Session(engine)
