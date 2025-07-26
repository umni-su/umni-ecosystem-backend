import time
from datetime import datetime

import schedule
from functools import partial
from threading import Thread, Event
from typing import Callable, Dict, Optional, Any, List

from classes.logger import Logger
from services.scheduler.enums.schedule_frequency import ScheduleFrequency
from services.scheduler.models.task_config import TaskConfig
from services.scheduler.models.task_info import TaskInfo, TaskStatus
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
        name = task_name or func.__name__

        if name in self.tasks:
            Logger.err(f"Task '{name}' already exists")
            return False

        self.task_registry[name] = func
        Logger.info(f"📆 Registered task function: {name}")

        task_config = TaskConfig(
            name=name,
            func=name,
            args=args,
            kwargs=kwargs,
            max_retries=max_retries,
            retry_delay=retry_delay
        )

        self.tasks[name] = {
            'config': task_config,
            'schedule': schedule_cfg
        }

        self._schedule_task(name)
        return True

    def _schedule_task(self, task_name: str):
        """Планирование задачи с гарантированным next_run"""
        if task_name not in self.tasks:
            return

        task = self.tasks[task_name]
        schedule_cfg = task['schedule']
        task_func = partial(self._run_task, task_name)

        try:
            # Отменяем предыдущую задачу, если она существует
            old_job = self._find_schedule_job(task_name)
            job = None
            if old_job:
                schedule.cancel_job(old_job)

            # Для дней недели (понедельник-воскресенье)
            if schedule_cfg.frequency in [
                ScheduleFrequency.MONDAY, ScheduleFrequency.TUESDAY,
                ScheduleFrequency.WEDNESDAY, ScheduleFrequency.THURSDAY,
                ScheduleFrequency.FRIDAY, ScheduleFrequency.SATURDAY,
                ScheduleFrequency.SUNDAY
            ]:
                scheduler = getattr(schedule.every(), schedule_cfg.frequency.value)
                if schedule_cfg.at_time:
                    job = scheduler.at(schedule_cfg.at_time).do(task_func)
                else:
                    job = scheduler.do(task_func)

            # Для дней с интервалом
            elif schedule_cfg.frequency == ScheduleFrequency.DAY:
                job = schedule.every(schedule_cfg.interval).days
                if schedule_cfg.at_time:
                    job = job.at(schedule_cfg.at_time).do(task_func)
                else:
                    job = job.do(task_func)

            # Для часов
            elif schedule_cfg.frequency == ScheduleFrequency.HOUR:
                job = schedule.every(schedule_cfg.interval).hours.do(task_func)

            # Для минут
            elif schedule_cfg.frequency == ScheduleFrequency.MINUTE:
                job = schedule.every(schedule_cfg.interval).minutes.do(task_func)

            # Для недель
            elif schedule_cfg.frequency == ScheduleFrequency.WEEK:
                job = schedule.every(schedule_cfg.interval).weeks
                if schedule_cfg.at_time:
                    job = job.at(schedule_cfg.at_time).do(task_func)
                else:
                    job = job.do(task_func)

            # Сохраняем job в задаче для последующего доступа
            if job:
                task['job'] = job
                Logger.info(f"📆 Task '{task_name}' scheduled. Next run: {job.next_run}")

        except Exception as e:
            Logger.err(f"📆 Failed to schedule task '{task_name}': {str(e)}")

    def _run_task(self, task_name: str):
        """Выполнение задачи с корректным отображением next_run"""
        if task_name not in self.tasks:
            return

        task = self.tasks[task_name]
        config = task['config']
        func = self.task_registry.get(config.func)
        job = self._find_schedule_job(task_name)

        if not func:
            Logger.err(f"Function not found for task '{task_name}'")
            return

        try:
            # Фиксируем время перед выполнением
            start_time = datetime.now()

            # Выполняем задачу
            result = func(*config.args, **config.kwargs)

            # Обновляем информацию о выполнении
            if job:
                job.last_run = start_time  # Используем время начала выполнения
                job.last_result = "success"

                # Вручную вычисляем next_run для логирования
                if hasattr(job, 'period'):
                    next_run = start_time + job.period
                    Logger.info(f"✅ Task '{task_name}' completed. Next run: {next_run}")
                else:
                    Logger.info(f"✅ Task '{task_name}' completed")

            return result

        except Exception as e:
            error_msg = str(e)
            Logger.err(f"❌ Task '{task_name}' failed: {error_msg}")
            if job:
                job.last_run = datetime.now()
                job.last_result = f"error: {error_msg}"

            if config.max_retries > 0:
                time.sleep(config.retry_delay)
                self._run_task(task_name)

    def start(self) -> bool:
        """Запуск планировщика"""
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            Logger.warn("📆 Scheduler already running")
            return False

        self._stop_event.clear()

        def run_scheduler():
            Logger.info("📆 Scheduler started")
            while not self._stop_event.is_set():
                try:
                    schedule.run_pending()
                    time.sleep(1)
                except Exception as e:
                    Logger.err(f"📆 Scheduler error: {str(e)}")
                    time.sleep(5)

            Logger.info("📆 Scheduler stopped")

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

    def run_all_tasks_now(self) -> List[str]:
        """
        Немедленный запуск всех зарегистрированных задач
        Возвращает список имен запущенных задач
        """
        started_tasks = []
        for task_name in self.tasks:
            if self.run_task_now(task_name):
                started_tasks.append(task_name)
        return started_tasks

    def get_task_info(self, task_name: str) -> Optional[TaskInfo]:
        """Возвращает информацию о задаче с корректным next_run"""
        if task_name not in self.tasks:
            return None

        task_data = self.tasks[task_name]
        job = self._find_schedule_job(task_name)

        if job:
            # Вычисляем актуальное next_run
            next_run = self.get_next_run_time(task_name)
        else:
            next_run = None

        return TaskInfo(
            name=task_name,
            status=TaskStatus.ACTIVE if job and job.should_run else TaskStatus.PAUSED,
            next_run=next_run,
            frequency=task_data['schedule'].frequency.value,
            interval=task_data['schedule'].interval,
            at_time=task_data['schedule'].at_time,
            last_run=getattr(job, 'last_run', None),
            last_result=getattr(job, 'last_result', None)
        )

    def get_all_tasks_info(self) -> List[TaskInfo]:
        """
        Возвращает информацию о всех задачах
        """
        return [self.get_task_info(name) for name in self.tasks.keys()]

    def _find_schedule_job(self, task_name: str):
        """Находит job в расписании или возвращает сохраненный"""
        if task_name in self.tasks and 'job' in self.tasks[task_name]:
            return self.tasks[task_name]['job']

        task_func = partial(self._run_task, task_name)
        for job in schedule.jobs:
            if job.job_func == task_func:
                return job
        return None

    def pause_task(self, task_name: str) -> bool:
        """Приостанавливает задачу"""
        job = self._find_schedule_job(task_name)
        if job:
            job.cancel()
            return True
        return False

    def resume_task(self, task_name: str) -> bool:
        """Возобновляет задачу"""
        if task_name not in self.tasks:
            return False
        self._schedule_task(task_name)
        return True

    def get_next_run_time(self, task_name: str) -> Optional[datetime]:
        """Возвращает корректное время следующего выполнения задачи"""
        if task_name not in self.tasks:
            return None

        job = self._find_schedule_job(task_name)
        if not job:
            return None

        if hasattr(job, 'last_run') and hasattr(job, 'period'):
            return job.last_run + job.period
        return job.next_run
