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

from entities.storage import StorageEntity
from entities.user import UserEntity
from entities.configuration import ConfigurationEntity
from entities.device import DeviceEntity
from entities.sensor_entity import SensorEntity
from entities.sensor_history import SensorHistory
from entities.device_network_interfaces import DeviceNetworkInterface

from entities.camera import CameraEntity
from entities.camera_area import CameraAreaEntity
from entities.camera_event import CameraEventEntity

from entities.location import LocationEntity
from entities.notification import NotificationEntity
from entities.rule_entity import RuleEntity, RuleNode, RuleEdge
from entities.notification_queue import NotificationQueueEntity
from entities.plugin_entity import PluginEntity
