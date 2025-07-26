import time
from datetime import datetime

from classes.tasks.camera_cleanup_task import CameraCleanupManager
from services.base_service import BaseService
from services.scheduler.classes.task_scheduler import TaskScheduler
from services.scheduler.enums.schedule_frequency import ScheduleFrequency
from services.scheduler.models.task_schedule import TaskSchedule


class SchedulerService(BaseService):
    def run(self):
        # Создаем планировщик
        scheduler = TaskScheduler()

        def camera_cleanup_task():
            # Инициализация
            cleanup_manager = CameraCleanupManager()

            # Запуск очистки для всех камер
            cleanup_manager.run_cleanup_for_all_cameras()
            # print("!!!! camera_cleanup_task RUN")

        # Добавляем задачи

        scheduler.add_task(
            func=camera_cleanup_task,
            schedule_cfg=TaskSchedule(
                frequency=ScheduleFrequency.DAY,
                interval=1,
                at_time="17:05"
            )
        )

        # Запускаем планировщик в фоновом режиме
        scheduler.start()
