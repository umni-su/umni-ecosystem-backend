import os

from importlib import import_module

from classes.logger import Logger
from classes.storages.filesystem import Filesystem
from services.base_service import BaseService


class ServiceRunner:
    services: list[BaseService] = []

    def __init__(self):
        name = 'services'
        root = f'./{name}'
        list = os.listdir(root)
        for item in list:
            class_dir = os.path.join(root, item)
            if not item.startswith(('__', '.')) and os.path.isdir(class_dir):
                # Dynamically import the module
                service_name = '_'.join([item, 'service'])
                service_main_file = os.path.join(
                    class_dir,
                    '.'.join([service_name, 'py'])
                )
                service_main_file = os.path.normpath(service_main_file)
                service_main_class = self.get_service_class_name(service_name)
                if Filesystem.exists(service_main_file):
                    try:
                        service_module = import_module(f'{name}.{item}.{service_name}')
                        Logger.debug(f'Run service {service_main_class} from {service_main_file}')
                        service_class = getattr(service_module, service_main_class)
                        service_instance: BaseService = service_class()
                        self.services.append(service_instance)
                    except Exception as e:
                        Logger.err(e)

    def get_service_class_name(self, name: str):
        __name__ = ''
        expl = name.split('_')
        for chunk in expl:
            __name__ += chunk.capitalize()
        return __name__

    def create_service(self, name: str):
        print(f'Create service: {name}')
