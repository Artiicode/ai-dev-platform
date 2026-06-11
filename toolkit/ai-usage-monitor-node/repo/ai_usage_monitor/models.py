"""Shared data models used across providers and the UI layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class TokenBreakdown:
    """Token counts for a single event or an aggregate bucket."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0

    @property
    def total(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_read_tokens
            + self.cache_creation_tokens
        )

    def __iadd__(self, other: "TokenBreakdown") -> "TokenBreakdown":
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.cache_read_tokens += other.cache_read_tokens
        self.cache_creation_tokens += other.cache_creation_tokens
        return self


@dataclass
class UsageEvent:
    """A single billable request (one assistant turn / API call)."""

    timestamp: float  # unix seconds
    model: str
    tokens: TokenBreakdown
    cost_usd: float = 0.0
    source: str = ""  # "cursor" | "claude"
    session_id: str = ""


@dataclass
class DailyUsage:
    day: date
    tokens: TokenBreakdown = field(default_factory=TokenBreakdown)
    cost_usd: float = 0.0
    events: int = 0


@dataclass
class ModelUsage:
    model: str
    tokens: TokenBreakdown = field(default_factory=TokenBreakdown)
    cost_usd: float = 0.0
    events: int = 0


@dataclass
class PlanStatus:
    """High-level subscription / spend status shown in the overview cards."""

    plan_name: str = "Unknown"
    # Percent of included plan used (0-100). None when not applicable.
    used_percent: Optional[float] = None
    auto_percent: Optional[float] = None
    api_percent: Optional[float] = None
    # Dollar figures (when available).
    spend_usd: Optional[float] = None
    limit_usd: Optional[float] = None
    on_demand_usd: Optional[float] = None
    bonus_usd: Optional[float] = None
    # Cost incurred in the current calendar month (USD).
    month_cost_usd: Optional[float] = None
    billing_cycle_start: Optional[str] = None
    billing_cycle_end: Optional[str] = None
    # When the quota/cycle resets (unix seconds) and a short label for it.
    reset_at: Optional[float] = None
    reset_label: str = ""
    # Spend within the current reset window (e.g. the active 5h block).
    block_cost_usd: Optional[float] = None
    message: str = ""


@dataclass
class RateWindow:
    """A Claude rolling rate-limit window (mirrors `/usage`)."""

    name: str  # e.g. "Current session", "Current week (all models)"
    utilization: float  # 0-100
    resets_at: Optional[float] = None  # unix seconds


@dataclass
class SessionBlock:
    """Stats for the most recent Claude Code session (mirrors `/usage` Session)."""

    cost_usd: float = 0.0
    wall_seconds: float = 0.0
    tokens: TokenBreakdown = field(default_factory=TokenBreakdown)
    requests: int = 0
    session_id: str = ""


@dataclass
class ProviderSnapshot:
    """Everything one provider knows at a point in time."""

    source: str  # "cursor" | "claude"
    available: bool = False
    error: str = ""
    plan: PlanStatus = field(default_factory=PlanStatus)
    daily: list[DailyUsage] = field(default_factory=list)
    by_model: list[ModelUsage] = field(default_factory=list)
    recent_events: list[UsageEvent] = field(default_factory=list)
    estimated_total_cost: float = 0.0
    is_estimated_cost: bool = True
    # Claude-specific: server-side rolling windows + current session stats.
    rate_windows: list[RateWindow] = field(default_factory=list)
    session: Optional[SessionBlock] = None
