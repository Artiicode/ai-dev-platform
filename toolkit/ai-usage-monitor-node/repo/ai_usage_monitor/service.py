"""Coordinates providers and produces a combined dashboard snapshot."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from .config import Settings
from .models import ProviderSnapshot
from .providers import claude_provider, cursor_provider


@dataclass
class DashboardData:
    cursor: ProviderSnapshot
    claude: ProviderSnapshot


def load_dashboard(settings: Settings | None = None) -> DashboardData:
    """Fetch both providers concurrently. Network/IO bound, so threads help."""
    settings = settings or Settings.load()
    with ThreadPoolExecutor(max_workers=2) as pool:
        cursor_future = pool.submit(_safe, cursor_provider.get_snapshot, settings, "cursor")
        claude_future = pool.submit(_safe, claude_provider.get_snapshot, settings, "claude")
        return DashboardData(
            cursor=cursor_future.result(),
            claude=claude_future.result(),
        )


def _safe(fn, settings: Settings, source: str) -> ProviderSnapshot:
    try:
        return fn(settings)
    except Exception as exc:  # pragma: no cover - defensive
        snap = ProviderSnapshot(source=source)
        snap.error = f"Unexpected error: {exc}"
        return snap
