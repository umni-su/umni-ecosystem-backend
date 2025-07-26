from pydantic import BaseModel


class SchedulerConfig(BaseModel):
    """Конфигурация планировщика"""
    check_interval: float = 1.0
    max_concurrent_tasks: int = 10
    log_level: str = "INFO"
