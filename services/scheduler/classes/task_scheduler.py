import time
import schedule
from functools import partial
from threading import Thread, Event
from typing import Callable, Dict, Optional, Any

from classes.logger import Logger
from services.scheduler.enums.schedule_frequency import ScheduleFrequency
from services.scheduler.models.task_config import TaskConfig
from services.scheduler.models.task_schedule import TaskSchedule


class TaskScheduler:
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.task_registry: Dict[str, Callable] = {}
        self._stop_event = Event()
        self._scheduler_thread = None

    def add_task(
            self,
            func: Callable,
            schedule_cfg: TaskSchedule,
            task_name: Optional[str] = None,
            args: tuple = (),
            kwargs: dict = {},
            max_retries: int = 0,
            retry_delay: float = 1.0
    ) -> bool:
        """
        Добавляет и регистрирует задачу в одном методе

        :param func: Функция для выполнения
        :param schedule_cfg: Конфигурация расписания
        :param task_name: Имя задачи (если None, будет использовано имя функции)
        :param args: Аргументы функции
        :param kwargs: Именованные аргументы функции
        :param max_retries: Максимальное количество повторов при ошибке
        :param retry_delay: Задержка между повторами (в секундах)
        """
        # Используем имя функции, если имя задачи не указано
        name = task_name or func.__name__

        # Проверяем, не зарегистрирована ли уже задача с таким именем
        if name in self.tasks:
            Logger.err(f"Task '{name}' already exists")
            return False

        # Регистрируем функцию
        self.task_registry[name] = func
        Logger.info(f"Registered task function: {name}")

        # Создаем конфиг задачи
        # task_config = {
        #     'func': name,
        #     'args': args,
        #     'kwargs': kwargs,
        #     'max_retries': max_retries,
        #     'retry_delay': retry_delay
        # }
        task_config = TaskConfig(
            name=name,
            func=name,
            args=args,
            kwargs=kwargs,
            max_retries=max_retries,
            retry_delay=retry_delay
        )

        # Сохраняем задачу
        self.tasks[name] = {
            'config': task_config,
            'schedule': schedule_cfg
        }

        # Планируем задачу
        self._schedule_task(name)
        return True

    def _schedule_task(self, task_name: str):
        """Планирование задачи (внутренний метод)"""
        task = self.tasks[task_name]
        schedule_cfg = task['schedule']
        task_func = partial(self._run_task, task_name)

        frequency_map = {
            ScheduleFrequency.MINUTE: 'minutes',
            ScheduleFrequency.HOUR: 'hours',
            ScheduleFrequency.DAY: 'days',
            ScheduleFrequency.WEEK: 'weeks',
            ScheduleFrequency.MONDAY: 'monday',
            ScheduleFrequency.TUESDAY: 'tuesday',
            ScheduleFrequency.WEDNESDAY: 'wednesday',
            ScheduleFrequency.THURSDAY: 'thursday',
            ScheduleFrequency.FRIDAY: 'friday',
            ScheduleFrequency.SATURDAY: 'saturday',
            ScheduleFrequency.SUNDAY: 'sunday'
        }

        frequency = frequency_map.get(schedule_cfg.frequency)
        if not frequency:
            Logger.err(f"Unsupported frequency: {schedule_cfg.frequency}")
            return

        try:
            # Для дней недели
            if schedule_cfg.frequency in [
                ScheduleFrequency.MONDAY, ScheduleFrequency.TUESDAY,
                ScheduleFrequency.WEDNESDAY, ScheduleFrequency.THURSDAY,
                ScheduleFrequency.FRIDAY, ScheduleFrequency.SATURDAY,
                ScheduleFrequency.SUNDAY
            ]:
                scheduler = getattr(schedule.every(), frequency)
                if schedule_cfg.at_time:
                    job = scheduler.at(schedule_cfg.at_time).do(task_func)
                else:
                    job = scheduler.do(task_func)
            # Для минут/часов/дней/недель
            else:
                job = getattr(schedule.every(schedule_cfg.interval), frequency).do(task_func)
                if schedule_cfg.at_time and frequency in ['days', 'weeks']:
                    job.at(schedule_cfg.at_time)

            Logger.info(
                f"Scheduled task '{task_name}' to run every {schedule_cfg.interval} {frequency} at {schedule_cfg.at_time or 'default time'}")
        except Exception as e:
            Logger.err(f"Failed to schedule task '{task_name}': {str(e)}")

    def _run_task(self, task_name: str):
        """Выполнение задачи"""
        if task_name not in self.tasks:
            return

        task = self.tasks[task_name]
        config = task['config']
        func = self.task_registry[config.func]

        try:
            func(*config.args, **config.kwargs)
        except Exception as e:
            Logger.err(f"Task '{task_name}' failed: {str(e)}")
            if config.max_retries > 0:
                time.sleep(config.retry_delay)
                self._run_task(task_name)  # Рекурсивный повтор

    def start(self) -> bool:
        """Запуск планировщика"""
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            Logger.warn("Scheduler already running")
            return False

        self._stop_event.clear()

        def run_scheduler():
            Logger.info("Scheduler started")
            while not self._stop_event.is_set():
                try:
                    schedule.run_pending()
                    time.sleep(1)
                except Exception as e:
                    Logger.err(f"Scheduler error: {str(e)}")
                    time.sleep(5)

            Logger.info("Scheduler stopped")

        self._scheduler_thread = Thread(target=run_scheduler, daemon=True)
        self._scheduler_thread.start()
        return True

    def stop(self) -> bool:
        """Остановка планировщика"""
        if not self._scheduler_thread or not self._scheduler_thread.is_alive():
            Logger.warn("Scheduler not running")
            return False

        self._stop_event.set()
        self._scheduler_thread.join(timeout=5)
        Logger.info("Scheduler stopped successfully")
        return True

    def run_task_now(self, task_name: str) -> bool:
        """Немедленный запуск задачи"""
        if task_name not in self.tasks:
            Logger.err(f"Task '{task_name}' not found")
            return False

        Thread(target=self._run_task, args=(task_name,), daemon=True).start()
        return True
