from datetime import datetime
from typing import Union

from classes.charts.chart_type import ChartType
from pydantic import BaseModel


class ChartSeries(BaseModel):
    name: str | None = None
    type: ChartType = ChartType.LINE
    data: list[list[Union[str | datetime | int | float], Union[str, int | float]]] = []
