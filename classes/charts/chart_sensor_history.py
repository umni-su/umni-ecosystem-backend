from classes.charts.chart_base import BaseChart
from classes.charts.chart_series import ChartSeries
from classes.charts.chart_type import ChartType
from models.sensor_history_model import SensorHistoryModel
from models.sensor_model import SensorModelWithHistory


class SensorHistoryChart(BaseChart):
    series: list[ChartSeries] = []
    sensor: SensorModelWithHistory | None = None

    def __init__(self, sensor: SensorModelWithHistory):
        super().__init__()
        self.sensor = sensor

    def set_series(self, history: list[SensorHistoryModel]):
        series = ChartSeries()
        series.name = self.sensor.name
        series.type = ChartType.LINE
        data = []
        for d in history:
            val = round(float(d.value), 2)
            time = d.created
            data.append([time, val])
        series.data = data
        self.series.append(series)
