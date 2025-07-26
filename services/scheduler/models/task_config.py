from pydantic import BaseModel, Field


class TaskConfig(BaseModel):
    name: str
    func: str
    args: tuple = ()
    kwargs: dict = {}
    max_retries: int = 0
    retry_delay: float = 1.0
