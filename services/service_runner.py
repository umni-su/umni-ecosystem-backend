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

import os

from importlib import import_module

from classes.configuration.configuration import EcosystemDatabaseConfiguration
from classes.logger.logger import Logger
from classes.logger.logger_types import LoggerType
from classes.storages.filesystem import Filesystem
from services.base_service import BaseService


class ServiceRunner:
    services: list[BaseService] = []
    config: EcosystemDatabaseConfiguration

    def __init__(self, config: EcosystemDatabaseConfiguration):
        self.config = config
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
                        Logger.debug(f'⏩  Run service {service_main_class} from {service_main_file}',
                                     LoggerType.SERVICES)
                        service_class = getattr(service_module, service_main_class)
                        service_instance: BaseService = service_class(self.config)
                        self.services.append(service_instance)
                    except Exception as e:
                        Logger.err(f"⏩ ServiceRunner __init__ {e}", LoggerType.SERVICES)

    def get_service_class_name(self, name: str):
        __name__ = ''
        expl = name.split('_')
        for chunk in expl:
            __name__ += chunk.capitalize()
        return __name__

    def create_service(self, name: str):
        Logger.debug(f'⏩ Create service: {name}', LoggerType.SERVICES)
