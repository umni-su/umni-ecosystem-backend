from classes.charts.chart_base import BaseChart
from classes.charts.chart_series import ChartSeries
from models.sensor_history_model import SensorHistoryChartModel


class SensorHistoryChart(BaseChart):
    def __init__(self, history: list[SensorHistoryChartModel]):
        super().__init__()
        series: ChartSeries = ChartSeries(history)
        self.series.append(series)
