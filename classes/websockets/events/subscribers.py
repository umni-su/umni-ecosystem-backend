# Copyright (C) 2025 Mikhail Sazanov
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from classes.events.event_bus import event_handler, event_bus
from classes.events.event_types import EventType
from classes.websockets.messages.ws_message_device_onoff import WebsocketMessageDeviceOnline, \
    WebsocketMessageDeviceOffline
from classes.websockets.messages.ws_message_rule_executed import WebsocketMessageRuleExecuted
from classes.websockets.websockets import WebSockets
from models.device_model import DeviceModel
from models.rule_model import NodeVisualize, EdgeCreate


def on_rule_executed(rule_id: int, nodes: list[NodeVisualize], edges: list[EdgeCreate]):
    WebSockets.send_broadcast(
        WebsocketMessageRuleExecuted(
            rule_id=rule_id,
            nodes=nodes,
            edges=edges
        )
    )


def on_device_online(device: DeviceModel):
    WebSockets.send_broadcast(
        WebsocketMessageDeviceOnline(
            device=device
        )
    )


def on_device_offline(device: DeviceModel):
    WebSockets.send_broadcast(
        WebsocketMessageDeviceOffline(
            device=device
        )
    )


def register_non_auto_subscribers():
    event_bus.subscribe(EventType.DEVICE_ONLINE, on_device_online)
    event_bus.subscribe(EventType.DEVICE_OFFLINE, on_device_offline)
    event_bus.subscribe(EventType.RULE_EXECUTED, on_rule_executed)
