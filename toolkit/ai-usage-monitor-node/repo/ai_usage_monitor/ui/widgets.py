"""Reusable UI widgets: cards, usage bars, metric labels."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from . import theme


class Card(QFrame):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Card")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(8)

    def layout(self) -> QVBoxLayout:  # type: ignore[override]
        return self._layout


class UsageBar(QWidget):
    """A thin horizontal progress bar colored by usage threshold."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._percent = 0.0
        self.setFixedHeight(10)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_percent(self, percent: float | None) -> None:
        self._percent = max(0.0, min(100.0, percent or 0.0))
        self.setToolTip("n/a" if percent is None else f"{percent:.1f}%")
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt signature)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        radius = self.height() / 2
        # Track
        painter.setBrush(QColor(theme.BG_ELEVATED))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), radius, radius)
        # Fill
        if self._percent > 0:
            w = int(self.width() * self._percent / 100.0)
            if w > 0:
                painter.setBrush(QColor(theme.usage_color(self._percent)))
                painter.drawRoundedRect(0, 0, max(w, int(self.height())), self.height(), radius, radius)
        painter.end()


def metric(value: str, caption: str) -> QWidget:
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(2)
    val = QLabel(value)
    val.setObjectName("Metric")
    cap = QLabel(caption)
    cap.setObjectName("Muted")
    lay.addWidget(val)
    lay.addWidget(cap)
    return w


def labeled_bar(label: str, percent: float | None) -> tuple[QWidget, UsageBar]:
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(4)
    row = QHBoxLayout()
    name = QLabel(label)
    name.setObjectName("Secondary")
    pct = QLabel("n/a" if percent is None else f"{percent:.0f}%")
    pct.setObjectName("Secondary")
    pct.setAlignment(Qt.AlignRight)
    row.addWidget(name)
    row.addWidget(pct)
    bar = UsageBar()
    bar.set_percent(percent)
    lay.addLayout(row)
    lay.addWidget(bar)
    return w, bar
