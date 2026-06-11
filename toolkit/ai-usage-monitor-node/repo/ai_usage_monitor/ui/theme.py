"""Windows 11 Fluent-inspired dark theme tokens and stylesheet."""

from __future__ import annotations

# Color tokens (Win11 dark, mica-ish).
BG = "#202020"
BG_CARD = "#2b2b2b"
BG_ELEVATED = "#323232"
STROKE = "#3d3d3d"
TEXT = "#ffffff"
TEXT_SECONDARY = "#c8c8c8"
TEXT_MUTED = "#909090"
ACCENT = "#4cc2ff"
ACCENT_DIM = "#2a6f8e"

# Brand accents.
CURSOR_COLOR = "#7aa2f7"
CLAUDE_COLOR = "#d97757"

# Usage bar thresholds.
OK = "#3fb950"
WARN = "#d29922"
DANGER = "#f85149"


def usage_color(percent: float | None) -> str:
    if percent is None:
        return TEXT_MUTED
    if percent >= 90:
        return DANGER
    if percent >= 75:
        return WARN
    return OK


STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-family: "Segoe UI", "Segoe UI Variable", sans-serif;
    font-size: 13px;
}}
QFrame#Card {{
    background-color: {BG_CARD};
    border: 1px solid {STROKE};
    border-radius: 8px;
}}
QLabel#H1 {{ font-size: 20px; font-weight: 600; }}
QLabel#H2 {{ font-size: 15px; font-weight: 600; }}
QLabel#Muted {{ color: {TEXT_MUTED}; }}
QLabel#Secondary {{ color: {TEXT_SECONDARY}; }}
QLabel#Metric {{ font-size: 22px; font-weight: 600; }}
QPushButton {{
    background-color: {BG_ELEVATED};
    border: 1px solid {STROKE};
    border-radius: 6px;
    padding: 6px 14px;
    color: {TEXT};
}}
QPushButton:hover {{ background-color: #3a3a3a; }}
QPushButton:pressed {{ background-color: #444; }}
QPushButton#Accent {{
    background-color: {ACCENT_DIM};
    border: 1px solid {ACCENT};
}}
QPushButton#Accent:hover {{ background-color: {ACCENT}; color: #06222e; }}
QTabWidget::pane {{ border: none; }}
QTabBar::tab {{
    background: transparent;
    color: {TEXT_MUTED};
    padding: 8px 16px;
    border: none;
    border-bottom: 2px solid transparent;
}}
QTabBar::tab:selected {{
    color: {TEXT};
    border-bottom: 2px solid {ACCENT};
}}
QTableWidget {{
    background-color: {BG_CARD};
    border: 1px solid {STROKE};
    border-radius: 8px;
    gridline-color: {STROKE};
    selection-background-color: {ACCENT_DIM};
}}
QHeaderView::section {{
    background-color: {BG_ELEVATED};
    color: {TEXT_SECONDARY};
    border: none;
    border-bottom: 1px solid {STROKE};
    padding: 6px;
}}
QLineEdit, QSpinBox, QCheckBox {{
    background-color: {BG_ELEVATED};
    border: 1px solid {STROKE};
    border-radius: 6px;
    padding: 6px;
    color: {TEXT};
}}
QScrollArea {{ border: none; }}
"""
