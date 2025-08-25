#  Copyright (C) 2025 Mikhail Sazanov
#  #
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#  #
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#  #
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

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
