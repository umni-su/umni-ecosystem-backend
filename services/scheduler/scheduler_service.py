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

from classes.tasks.camera_cleanup_task import CameraCleanupManager
from services.base_service import BaseService
from services.scheduler.classes.task_scheduler import scheduler
from services.scheduler.enums.schedule_frequency import ScheduleFrequency
from services.scheduler.models.task_schedule import TaskSchedule


class SchedulerService(BaseService):
    name = 'scheduler'

    def run(self):
        # Создаем планировщик
        def camera_cleanup_task():
            cleanup_manager = CameraCleanupManager()
            cleanup_manager.run_cleanup_for_all_cameras()

        # Добавляем задачи для камер
        scheduler.add_task(
            func=camera_cleanup_task,
            schedule_cfg=TaskSchedule(
                frequency=ScheduleFrequency.MINUTE,
                interval=30
            )
        )

        # Запускаем планировщик в фоновом режиме
        scheduler.start()

        cleanup_manager = CameraCleanupManager()
        cleanup_manager.run_cleanup_for_all_cameras()
