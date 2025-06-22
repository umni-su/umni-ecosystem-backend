from classes.charts.chart_series import ChartSeries


class BaseChart:
    series: list[ChartSeries] = []

    def __init__(self):
        self.series = []
