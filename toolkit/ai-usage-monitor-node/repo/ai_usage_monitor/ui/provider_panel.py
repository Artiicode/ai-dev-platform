"""A panel rendering one provider's snapshot: overview card + tabs."""

from __future__ import annotations

from datetime import datetime, timezone

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from . import theme
from .charts import DailyCostChart
from .widgets import Card, labeled_bar, metric
from ..models import ProviderSnapshot


def _fmt_usd(value) -> str:
    return "-" if value is None else f"${value:,.2f}"


def _fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def _countdown(reset_at) -> str:
    if not reset_at:
        return "-"
    delta = int(reset_at - datetime.now(timezone.utc).timestamp())
    if delta <= 0:
        return "now"
    days, rem = divmod(delta, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


class ProviderPanel(QWidget):
    def __init__(self, title: str, color: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._color = color
        self._show_cost = True
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        # Header
        header = QHBoxLayout()
        self.title = QLabel(title)
        self.title.setObjectName("H2")
        self.title.setStyleSheet(f"color: {color};")
        self.plan_label = QLabel("")
        self.plan_label.setObjectName("Muted")
        self.plan_label.setAlignment(Qt.AlignRight)
        header.addWidget(self.title)
        header.addStretch()
        header.addWidget(self.plan_label)
        root.addLayout(header)

        # Overview card
        self.card = Card()
        root.addWidget(self.card)

        # Tabs
        self.tabs = QTabWidget()
        self.chart = DailyCostChart(color)
        self.tabs.addTab(self.chart, "Daily")
        self.model_table = self._make_table(["Model", "Events", "Tokens", "Cost"])
        self.tabs.addTab(self.model_table, "By Model")
        self.events_table = self._make_table(
            ["Time", "Model", "Tokens", "Cost"]
        )
        self.tabs.addTab(self.events_table, "Recent")
        root.addWidget(self.tabs, 1)

    def _make_table(self, headers: list[str]) -> QTableWidget:
        t = QTableWidget(0, len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.verticalHeader().setVisible(False)
        t.setEditTriggers(QTableWidget.NoEditTriggers)
        t.setSelectionBehavior(QTableWidget.SelectRows)
        t.horizontalHeader().setStretchLastSection(True)
        t.setColumnWidth(0, 220)
        return t

    def set_show_cost(self, show: bool) -> None:
        self._show_cost = show

    def update_snapshot(self, snap: ProviderSnapshot) -> None:
        self._render_card(snap)
        # Estimated-cost providers chart tokens rather than estimated dollars.
        use_cost = self._show_cost and not snap.is_estimated_cost
        self.chart.set_data(snap.daily, use_cost=use_cost)
        self._fill_model_table(snap)
        self._fill_events_table(snap)

    # --- rendering helpers ---

    def _clear_card(self) -> None:
        lay = self.card.layout()
        while lay.count():
            item = lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _render_card(self, snap: ProviderSnapshot) -> None:
        self._clear_card()
        lay = self.card.layout()
        self.plan_label.setText(snap.plan.plan_name if snap.available else "")

        if not snap.available:
            err = QLabel(snap.error or "No data available.")
            err.setObjectName("Muted")
            err.setWordWrap(True)
            lay.addWidget(err)
            return

        plan = snap.plan

        # Estimated-cost providers (Claude) never show dollar figures.
        show_money = self._show_cost and not snap.is_estimated_cost

        # Metric row
        metrics = QHBoxLayout()
        if show_money:
            if plan.month_cost_usd is not None:
                metrics.addWidget(metric(_fmt_usd(plan.month_cost_usd), "This cycle"))
            if plan.limit_usd is not None:
                metrics.addWidget(metric(_fmt_usd(plan.limit_usd), "Included limit"))
            if plan.on_demand_usd is not None:
                metrics.addWidget(metric(_fmt_usd(plan.on_demand_usd), "On-demand"))
            if plan.block_cost_usd is not None:
                metrics.addWidget(metric(_fmt_usd(plan.block_cost_usd), "5h block"))
        if plan.reset_at:
            metrics.addWidget(metric(_countdown(plan.reset_at), f"{plan.reset_label} reset"))
        metrics.addStretch()
        wrap = QWidget()
        wrap.setLayout(metrics)
        lay.addWidget(wrap)

        # Usage bars (Cursor)
        if plan.used_percent is not None:
            w, _ = labeled_bar("Total usage", plan.used_percent)
            lay.addWidget(w)
        if plan.auto_percent is not None:
            w, _ = labeled_bar("Auto", plan.auto_percent)
            lay.addWidget(w)
        if plan.api_percent is not None:
            w, _ = labeled_bar("API / manual", plan.api_percent)
            lay.addWidget(w)

        # Rolling rate-limit windows (Claude /usage style)
        for win in snap.rate_windows:
            label = win.name
            if win.resets_at:
                label += f"  ·  resets in {_countdown(win.resets_at)}"
            w, _ = labeled_bar(label, win.utilization)
            lay.addWidget(w)

        # Session block (Claude /usage style)
        if snap.session is not None and snap.session.requests:
            s = snap.session
            t = s.tokens
            bits = [
                f"Session: {_fmt_tokens(t.total)} tokens",
                f"{s.requests} reqs",
            ]
            if show_money:
                bits.insert(0, _fmt_usd(s.cost_usd))
            sess = QLabel("   •   ".join(bits))
            sess.setObjectName("Muted")
            lay.addWidget(sess)

        # Billing cycle / message
        meta_bits = []
        if plan.billing_cycle_start and plan.billing_cycle_end:
            meta_bits.append(
                f"Cycle: {plan.billing_cycle_start} → {plan.billing_cycle_end}"
            )
        if plan.message:
            meta_bits.append(plan.message)
        if snap.is_estimated_cost:
            meta_bits.append("Cost is a local estimate.")
        if meta_bits:
            meta = QLabel("   •   ".join(meta_bits))
            meta.setObjectName("Muted")
            meta.setWordWrap(True)
            lay.addWidget(meta)

    def _fill_model_table(self, snap: ProviderSnapshot) -> None:
        # Estimated-cost providers (Claude) show token share % instead of $.
        show_money = self._show_cost and not snap.is_estimated_cost
        t = self.model_table
        t.setHorizontalHeaderItem(3, QTableWidgetItem("Cost" if show_money else "Share"))
        total_tokens = sum(m.tokens.total for m in snap.by_model) or 1
        rows = (
            snap.by_model
            if show_money
            else sorted(snap.by_model, key=lambda m: m.tokens.total, reverse=True)
        )
        t.setRowCount(len(rows))
        for i, m in enumerate(rows):
            t.setItem(i, 0, QTableWidgetItem(m.model))
            t.setItem(i, 1, QTableWidgetItem(str(m.events)))
            t.setItem(i, 2, QTableWidgetItem(_fmt_tokens(m.tokens.total)))
            if show_money:
                last = _fmt_usd(m.cost_usd)
            else:
                last = f"{m.tokens.total / total_tokens * 100:.1f}%"
            t.setItem(i, 3, QTableWidgetItem(last))

    def _fill_events_table(self, snap: ProviderSnapshot) -> None:
        show_money = self._show_cost and not snap.is_estimated_cost
        t = self.events_table
        t.setHorizontalHeaderItem(3, QTableWidgetItem("Cost" if show_money else "Tokens%"))
        total_tokens = sum(e.tokens.total for e in snap.recent_events) or 1
        t.setRowCount(len(snap.recent_events))
        for i, e in enumerate(snap.recent_events):
            if e.timestamp:
                ts = datetime.fromtimestamp(e.timestamp).strftime("%m/%d %H:%M")
            else:
                ts = "-"
            t.setItem(i, 0, QTableWidgetItem(ts))
            t.setItem(i, 1, QTableWidgetItem(e.model))
            t.setItem(i, 2, QTableWidgetItem(_fmt_tokens(e.tokens.total)))
            if show_money:
                last = _fmt_usd(e.cost_usd)
            else:
                last = f"{e.tokens.total / total_tokens * 100:.1f}%"
            t.setItem(i, 3, QTableWidgetItem(last))
