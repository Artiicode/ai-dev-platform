"""Main application window."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QObject, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from . import theme
from .provider_panel import ProviderPanel
from .settings_dialog import SettingsDialog
from ..config import Settings
from ..service import DashboardData, load_dashboard


class _RefreshWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, settings: Settings):
        super().__init__()
        self._settings = settings

    def run(self) -> None:
        try:
            data = load_dashboard(self._settings)
            self.finished.emit(data)
        except Exception as exc:  # pragma: no cover - defensive
            self.failed.emit(str(exc))


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Usage Monitor")
        self.resize(1100, 720)
        self.settings = Settings.load()
        self._thread: QThread | None = None
        self._worker: _RefreshWorker | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(14)

        # Top bar
        top = QHBoxLayout()
        title = QLabel("AI Usage Monitor")
        title.setObjectName("H1")
        self.status = QLabel("")
        self.status.setObjectName("Muted")
        self.refresh_btn = QPushButton("\u21bb  Refresh")
        self.refresh_btn.setObjectName("Accent")
        self.refresh_btn.clicked.connect(self.refresh)
        self.settings_btn = QPushButton("\u2699  Settings")
        self.settings_btn.clicked.connect(self.open_settings)
        top.addWidget(title)
        top.addSpacing(12)
        top.addWidget(self.status)
        top.addStretch()
        top.addWidget(self.refresh_btn)
        top.addWidget(self.settings_btn)
        root.addLayout(top)

        # Two provider panels side by side
        panels = QHBoxLayout()
        panels.setSpacing(16)
        self.cursor_panel = ProviderPanel("Cursor", theme.CURSOR_COLOR)
        self.claude_panel = ProviderPanel("Claude Code", theme.CLAUDE_COLOR)
        panels.addWidget(self.cursor_panel, 1)
        panels.addWidget(self.claude_panel, 1)
        root.addLayout(panels, 1)

        self._apply_show_cost()

        # Auto-refresh timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self._configure_timer()

        QTimer.singleShot(100, self.refresh)

    def _apply_show_cost(self) -> None:
        self.cursor_panel.set_show_cost(self.settings.show_cost)
        self.claude_panel.set_show_cost(self.settings.show_cost)

    def _configure_timer(self) -> None:
        self.timer.stop()
        if self.settings.refresh_interval_seconds > 0:
            self.timer.start(self.settings.refresh_interval_seconds * 1000)

    def refresh(self) -> None:
        if self._thread is not None:
            return  # already running
        self.refresh_btn.setEnabled(False)
        self.status.setText("Refreshing\u2026")

        self._thread = QThread(self)
        self._worker = _RefreshWorker(self.settings)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._thread.start()

    def _cleanup_thread(self) -> None:
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait()
            self._thread = None
            self._worker = None
        self.refresh_btn.setEnabled(True)

    def _on_finished(self, data: DashboardData) -> None:
        self.cursor_panel.update_snapshot(data.cursor)
        self.claude_panel.update_snapshot(data.claude)
        self.status.setText(
            "Updated " + datetime.now().strftime("%H:%M:%S")
        )
        self._cleanup_thread()

    def _on_failed(self, message: str) -> None:
        self.status.setText("Refresh failed")
        QMessageBox.warning(self, "Refresh failed", message)
        self._cleanup_thread()

    def open_settings(self) -> None:
        dlg = SettingsDialog(self.settings, self)
        if dlg.exec():
            self.settings = dlg.apply_to()
            self.settings.save()
            self._apply_show_cost()
            self._configure_timer()
            self.refresh()

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt signature)
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait()
        event.accept()
