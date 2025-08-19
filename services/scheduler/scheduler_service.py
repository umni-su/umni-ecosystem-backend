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
                interval=20
            )
        )

        # Запускаем планировщик в фоновом режиме
        scheduler.start()
