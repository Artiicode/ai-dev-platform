"""Settings dialog for credentials, paths, and refresh behavior."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)

from ..config import Settings


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(520)
        self._settings = settings

        root = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)

        self.refresh = QSpinBox()
        self.refresh.setRange(0, 86400)
        self.refresh.setSuffix(" s")
        self.refresh.setValue(settings.refresh_interval_seconds)
        form.addRow("Auto-refresh interval (0 = off)", self.refresh)

        self.history = QSpinBox()
        self.history.setRange(1, 365)
        self.history.setSuffix(" days")
        self.history.setValue(settings.history_days)
        form.addRow("History window", self.history)

        self.show_cost = QCheckBox("Show estimated cost figures")
        self.show_cost.setChecked(settings.show_cost)
        form.addRow("", self.show_cost)

        self.cursor_token = QLineEdit(settings.cursor_session_token)
        self.cursor_token.setEchoMode(QLineEdit.Password)
        self.cursor_token.setPlaceholderText("WorkosCursorSessionToken cookie (optional)")
        form.addRow("Cursor session token", self.cursor_token)

        self.claude_dir = QLineEdit(settings.claude_config_dir)
        self.claude_dir.setPlaceholderText("Override Claude projects dir (optional)")
        form.addRow("Claude config dir", self.claude_dir)

        self.admin_key = QLineEdit(settings.cursor_admin_api_key)
        self.admin_key.setEchoMode(QLineEdit.Password)
        self.admin_key.setPlaceholderText("Enterprise Admin API key (optional)")
        form.addRow("Cursor Admin API key", self.admin_key)

        root.addLayout(form)

        hint = QLabel(
            "Cursor auto-detects your desktop login. The session token is only "
            "needed for detailed per-request events. Tokens are stored locally "
            "and never transmitted anywhere except the official APIs."
        )
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        root.addWidget(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def apply_to(self) -> Settings:
        s = self._settings
        s.refresh_interval_seconds = self.refresh.value()
        s.history_days = self.history.value()
        s.show_cost = self.show_cost.isChecked()
        s.cursor_session_token = self.cursor_token.text().strip()
        s.claude_config_dir = self.claude_dir.text().strip()
        s.cursor_admin_api_key = self.admin_key.text().strip()
        return s
