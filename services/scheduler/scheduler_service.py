from datetime import datetime

from classes.logger import Logger
from services.base_service import BaseService
from services.scheduler.classes.task_scheduler import TaskScheduler
from services.scheduler.enums.schedule_frequency import ScheduleFrequency
from services.scheduler.models.task_schedule import TaskSchedule


class SchedulerService(BaseService):
    def run(self):
        Logger.debug("📆 Scheduler Service started")

        # Создаем планировщик
        scheduler = TaskScheduler()

        # Регистрируем задачи
        def simple_task(name: str):
            """Простая задача"""
            print(f"Hello, {name}! Current time: {datetime.now()}")
            return f"Greeted {name} at {datetime.now()}"

        def camera_cleanup_task(probability: float = 0.3):
            pass

        # Добавляем задачи

        # 1. Простая задача с интервалом 10 секунд
        scheduler.add_task(
            func=simple_task,
            schedule_cfg=TaskSchedule(
                frequency=ScheduleFrequency.MINUTE,
                interval=1
            ),
            kwargs={"name": "Francine"},
        )

        # Запускаем планировщик в фоновом режиме
        scheduler.start()
