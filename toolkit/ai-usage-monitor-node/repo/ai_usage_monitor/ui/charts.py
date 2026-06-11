"""Chart widgets built on QtCharts (ships with PySide6)."""

from __future__ import annotations

from PySide6.QtCharts import (
    QBarCategoryAxis,
    QBarSeries,
    QBarSet,
    QChart,
    QChartView,
    QValueAxis,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget

from . import theme
from ..models import DailyUsage


class DailyCostChart(QChartView):
    """Bar chart of daily estimated cost (or tokens) over the history window."""

    def __init__(self, color: str, parent: QWidget | None = None):
        chart = QChart()
        chart.setBackgroundVisible(False)
        chart.legend().setVisible(False)
        chart.setTitleBrush(QColor(theme.TEXT))
        super().__init__(chart)
        self.setRenderHint(QPainter.Antialiasing)
        self.setStyleSheet("background: transparent;")
        self._color = color
        self._chart = chart

    def set_data(self, daily: list[DailyUsage], use_cost: bool = True) -> None:
        chart = self._chart
        chart.removeAllSeries()
        for ax in list(chart.axes()):
            chart.removeAxis(ax)

        if not daily:
            chart.setTitle("No data in selected window")
            return
        chart.setTitle("")

        bar_set = QBarSet("")
        bar_set.setColor(QColor(self._color))
        bar_set.setBorderColor(QColor(self._color))
        values = []
        categories = []
        for d in daily:
            v = d.cost_usd if use_cost else d.tokens.total
            values.append(v)
            categories.append(d.day.strftime("%m/%d"))
            bar_set.append(v)

        series = QBarSeries()
        series.append(bar_set)
        series.setBarWidth(0.85)
        chart.addSeries(series)

        axis_x = QBarCategoryAxis()
        # Avoid overcrowding: show at most ~12 labels.
        step = max(1, len(categories) // 12)
        axis_x.append(categories)
        axis_x.setLabelsColor(QColor(theme.TEXT_MUTED))
        axis_x.setGridLineVisible(False)
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)
        if step > 1:
            for i, c in enumerate(categories):
                if i % step != 0:
                    axis_x.replace(c, "")

        axis_y = QValueAxis()
        top = max(values) if values else 1
        axis_y.setRange(0, top * 1.15 if top > 0 else 1)
        axis_y.setLabelFormat("$%.2f" if use_cost else "%.0f")
        axis_y.setLabelsColor(QColor(theme.TEXT_MUTED))
        axis_y.setGridLineColor(QColor(theme.STROKE))
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)
