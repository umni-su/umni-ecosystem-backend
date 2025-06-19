from classes.charts.chart_type import ChartType
from models.sensor_history_model import SensorHistoryChartModel


class ChartSeries:
    name: str
    type: ChartType
    showSymbol: bool = True
    data: list[SensorHistoryChartModel]

    def __init__(self, data: list[SensorHistoryChartModel]):
        self.data = data
        # print(data)
        # for d in data:
        #     print(d.created)
        #     # value = SensorHistoryChartModel.model_validate(d)
        #     # data.append(value)
