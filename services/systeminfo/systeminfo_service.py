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

import time

from classes.thread.daemon import Daemon
from services.base_service import BaseService
import psutil

from services.systeminfo.models.all_memory_model import AllMemoryModel
from services.systeminfo.models.cpu_model import CpuModel
from services.systeminfo.models.disk_usage_model import DiskUsage
from services.systeminfo.models.drive_model import DriveModel
from services.systeminfo.models.memory_stat_model import MemoryModel
from services.systeminfo.models.net_usage_model import NetUsageModel
from services.systeminfo.models.systeminfo_model import SysteminfoModel


class SysteminfoService(BaseService):
    name = 'systeminfo'
    drives: list[DriveModel] = []
    memory: AllMemoryModel = AllMemoryModel()
    net: NetUsageModel
    cpu: CpuModel = CpuModel()
    daemon: Daemon = None
    info: SysteminfoModel | None = None

    def run(self):
        self.memory.swap = MemoryModel()
        self.memory.virtual = MemoryModel()
        self.daemon = Daemon(self.collect_systeminfo)

    def collect_systeminfo(self):
        while True:
            self.update_disk_stat()
            self.get_memory_stat()
            self.get_cpu_stat()
            self.get_net_stat()

            SysteminfoService.info = SysteminfoModel(
                disks=self.drives,
                net=self.net,
                memory=self.memory,
                cpu=self.cpu
            )

            time.sleep(1)

    @classmethod
    def get_existing_drive_index(cls, mountpoint: str):
        for __index__, __drive__ in enumerate(cls.drives):
            if __drive__.mountpoint == mountpoint:
                return __index__
        return None

    @classmethod
    def get_cpu_stat(cls):
        cls.cpu.last = psutil.cpu_percent(interval=1)
        if len(cls.cpu.values) > 30:
            cls.cpu.values.pop(0)
        cls.cpu.values.append(cls.cpu.last)

    @classmethod
    def get_net_stat(cls):
        net = psutil.net_io_counters()
        cls.net = NetUsageModel(
            bytes_sent=net.bytes_sent,
            bytes_received=net.bytes_recv,
            packets_sent=net.packets_sent,
            packets_received=net.packets_recv
        )

    '''
    Gets memory stat
    '''

    @classmethod
    def get_memory_stat(cls):
        ram = psutil.virtual_memory()
        swap = psutil.swap_memory()
        cls.memory.swap.total = swap.total
        cls.memory.swap.used = swap.used
        cls.memory.swap.free = swap.free
        cls.memory.swap.percent = swap.percent

        cls.memory.virtual.total = ram.total
        cls.memory.virtual.used = ram.used
        cls.memory.virtual.free = ram.free
        cls.memory.virtual.percent = ram.percent

        if len(cls.memory.virtual.values) > 30:
            cls.memory.virtual.values.pop(0)
        if len(cls.memory.swap.values) > 30:
            cls.memory.swap.values.pop(0)
        cls.memory.virtual.values.append(ram.percent)
        cls.memory.swap.values.append(swap.percent)

    '''
    Gets disks and disk usage
    '''

    @classmethod
    def update_disk_stat(cls):
        disks = psutil.disk_partitions(all=False)
        for part in disks:
            current_index = cls.get_existing_drive_index(part.mountpoint)
            if current_index is not None:
                drive = cls.drives[current_index]
            else:
                drive = DriveModel()

            stat = psutil.disk_usage(part.mountpoint)
            drive.device = part.device
            drive.mountpoint = part.mountpoint
            drive.fstype = part.fstype
            drive.opts = part.opts.split(',')
            drive.stat = DiskUsage(
                free=stat.free,
                total=stat.total,
                used=stat.used
            )
            if current_index is None:
                cls.drives.append(drive)
