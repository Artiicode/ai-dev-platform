"""Cursor provider.

Pulls plan/spend status and detailed usage events for an individual Cursor
account. Two paths:

1. Auto: read the JWT access token from Cursor desktop's SQLite store and call
   the dashboard RPC service (``api2.cursor.sh``).
2. Fallback: use a manually supplied ``WorkosCursorSessionToken`` cookie against
   the unofficial dashboard REST endpoints (``cursor.com/api/*``).

NOTE: These endpoints are unofficial/reverse-engineered and may change without
notice. All amounts from Cursor are in cents.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import requests

from ..cache import cached
from ..config import Settings, cursor_state_db_paths, cursor_token_files
from ..models import (
    DailyUsage,
    ModelUsage,
    PlanStatus,
    ProviderSnapshot,
    TokenBreakdown,
    UsageEvent,
)

_RPC_BASE = "https://api2.cursor.sh"
_WEB_BASE = "https://cursor.com"
_OAUTH_CLIENT_ID = "KbZUR41cY7W6zRSdpSUJ7I7mLYBKOCmB"
_TIMEOUT = 20


def _read_token_file() -> tuple[str | None, str | None, Path | None]:
    """Return (access_token, refresh_token, source_path) from the CLI auth file."""
    for path in cursor_token_files():
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        access = data.get("accessToken") or data.get("access_token")
        refresh = data.get("refreshToken") or data.get("refresh_token")
        if access:
            return str(access), (str(refresh) if refresh else None), path
    return None, None, None


def _read_token_sqlite() -> str | None:
    """Read cursorAuth/accessToken from the desktop SQLite store."""
    for db in cursor_state_db_paths():
        if not db.exists():
            continue
        try:
            uri = f"file:{db}?mode=ro&immutable=1"
            conn = sqlite3.connect(uri, uri=True, timeout=5)
            try:
                cur = conn.execute(
                    "SELECT value FROM ItemTable WHERE key = ?",
                    ("cursorAuth/accessToken",),
                )
                row = cur.fetchone()
                if row and row[0]:
                    return str(row[0]).strip('"')
            finally:
                conn.close()
        except sqlite3.Error:
            continue
    return None


def read_access_token() -> str | None:
    """Best-effort access token: prefer the CLI auth file, then desktop SQLite."""
    access, _, _ = _read_token_file()
    if access:
        return access
    return _read_token_sqlite()


def _refresh_token() -> str | None:
    """Refresh an expired access token and persist it back to the auth file."""
    _, refresh, path = _read_token_file()
    if not refresh:
        return None
    try:
        resp = requests.post(
            f"{_RPC_BASE}/oauth/token",
            json={
                "grant_type": "refresh_token",
                "client_id": _OAUTH_CLIENT_ID,
                "refresh_token": refresh,
            },
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        new_access = resp.json().get("access_token")
    except (requests.RequestException, ValueError):
        return None
    if not new_access:
        return None
    if path is not None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            data["accessToken"] = new_access
            path.write_text(json.dumps(data), encoding="utf-8")
        except (OSError, ValueError):
            pass
    return new_access


def _rpc(method: str, token: str) -> dict | None:
    url = f"{_RPC_BASE}/aiserver.v1.DashboardService/{method}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Connect-Protocol-Version": "1",
    }
    resp = requests.post(url, headers=headers, data="{}", timeout=_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _cents(value) -> float:
    try:
        return float(value) / 100.0
    except (TypeError, ValueError):
        return 0.0


def _plan_from_rpc(usage: dict, plan_info: dict | None) -> PlanStatus:
    plan = PlanStatus()
    pu = usage.get("planUsage", {}) if isinstance(usage, dict) else {}
    plan.spend_usd = _cents(pu.get("totalSpend"))
    plan.month_cost_usd = plan.spend_usd  # current billing cycle spend
    plan.bonus_usd = _cents(pu.get("bonusSpend")) if pu.get("bonusSpend") else None
    plan.limit_usd = _cents(pu.get("limit")) if pu.get("limit") else None
    plan.auto_percent = _safe_float(pu.get("autoPercentUsed"))
    plan.api_percent = _safe_float(pu.get("apiPercentUsed"))
    plan.used_percent = _safe_float(pu.get("totalPercentUsed"))

    sl = usage.get("spendLimitUsage", {}) if isinstance(usage, dict) else {}
    if sl:
        # Prefer the per-user figure on team plans; fall back to total.
        on_demand = sl.get("individualUsed")
        if on_demand is None:
            on_demand = sl.get("totalSpend")
        plan.on_demand_usd = _cents(on_demand)

    plan.billing_cycle_start = _iso_from_ms(usage.get("billingCycleStart"))
    plan.billing_cycle_end = _iso_from_ms(usage.get("billingCycleEnd"))
    plan.reset_at = _ms_to_seconds(usage.get("billingCycleEnd"))
    plan.reset_label = "billing cycle"
    plan.message = usage.get("displayMessage", "") if isinstance(usage, dict) else ""

    if plan_info and isinstance(plan_info, dict):
        info = plan_info.get("planInfo", plan_info)
        plan.plan_name = info.get("planName", "Cursor")
        if plan.limit_usd is None and info.get("includedAmountCents"):
            plan.limit_usd = _cents(info.get("includedAmountCents"))
    else:
        plan.plan_name = "Cursor"
    return plan


def _safe_float(value) -> float | None:
    try:
        f = float(value)
        return f if f == f else None  # filter NaN
    except (TypeError, ValueError):
        return None


def _ms_to_seconds(value) -> float | None:
    try:
        return float(value) / 1000.0
    except (TypeError, ValueError):
        return None


def _iso_from_ms(value) -> str | None:
    secs = _ms_to_seconds(value)
    if secs is None:
        return None
    return datetime.fromtimestamp(secs, tz=timezone.utc).date().isoformat()


def _fetch_events_cookie(token: str, settings: Settings) -> list[UsageEvent]:
    """Fetch detailed usage events via the cookie-authenticated REST endpoint."""
    session = requests.Session()
    session.cookies.set("WorkosCursorSessionToken", token, domain="cursor.com")
    session.headers["Origin"] = _WEB_BASE
    events: list[UsageEvent] = []
    body = {"page": 1, "pageSize": max(50, settings.recent_events_limit)}
    resp = session.post(
        f"{_WEB_BASE}/api/dashboard/get-filtered-usage-events",
        json=body,
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    for e in data.get("usageEventsDisplay", []):
        tu = e.get("tokenUsage") or {}
        tokens = TokenBreakdown(
            input_tokens=int(tu.get("inputTokens", 0) or 0),
            output_tokens=int(tu.get("outputTokens", 0) or 0),
            cache_creation_tokens=int(tu.get("cacheWriteTokens", 0) or 0),
        )
        cost = float(e.get("chargedCents", 0) or 0) / 100.0
        ts_ms = e.get("timestamp")
        try:
            ts = float(ts_ms) / 1000.0
        except (TypeError, ValueError):
            ts = 0.0
        events.append(
            UsageEvent(
                timestamp=ts,
                model=e.get("model", "unknown"),
                tokens=tokens,
                cost_usd=cost,
                source="cursor",
            )
        )
    return events


def _aggregate_events(events: list[UsageEvent], history_days: int):
    daily: dict[object, DailyUsage] = {}
    by_model: dict[str, ModelUsage] = {}
    now = datetime.now(timezone.utc).timestamp()
    cutoff = now - history_days * 86400 if history_days > 0 else 0
    for ev in events:
        if ev.timestamp and ev.timestamp >= cutoff:
            day = datetime.fromtimestamp(ev.timestamp, tz=timezone.utc).date()
            b = daily.get(day) or DailyUsage(day=day)
            b.tokens += ev.tokens
            b.cost_usd += ev.cost_usd
            b.events += 1
            daily[day] = b
        m = by_model.get(ev.model) or ModelUsage(model=ev.model)
        m.tokens += ev.tokens
        m.cost_usd += ev.cost_usd
        m.events += 1
        by_model[ev.model] = m
    return (
        sorted(daily.values(), key=lambda d: d.day),
        sorted(by_model.values(), key=lambda m: m.cost_usd, reverse=True),
    )


def _remote_plan_payload() -> tuple[dict | None, dict | None, str]:
    """Fetch (usage, plan_info, error) from the dashboard RPC, refreshing once."""
    token = read_access_token()
    if not token:
        return None, None, ""
    try:
        usage = _rpc("GetCurrentPeriodUsage", token)
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code in (401, 403):
            new_token = _refresh_token()
            if new_token:
                token = new_token
                try:
                    usage = _rpc("GetCurrentPeriodUsage", token)
                except requests.RequestException as exc2:
                    return None, None, f"Cursor RPC failed after refresh: {exc2}"
            else:
                return None, None, f"Cursor RPC failed: {exc}"
        else:
            return None, None, f"Cursor RPC failed: {exc}"
    except requests.RequestException as exc:
        return None, None, f"Cursor RPC failed: {exc}"

    plan_info = None
    try:
        plan_info = _rpc("GetPlanInfo", token)
    except requests.RequestException:
        plan_info = None
    return usage, plan_info, ""


def get_snapshot(settings: Settings) -> ProviderSnapshot:
    snap = ProviderSnapshot(source="cursor", is_estimated_cost=False)

    ttl = max(0, settings.api_min_interval_seconds)
    usage, plan_info, err = cached("cursor:plan", ttl, _remote_plan_payload)
    plan_ok = False
    if usage:
        snap.plan = _plan_from_rpc(usage, plan_info)
        snap.available = True
        plan_ok = True
    elif err:
        snap.error = err

    # Detailed per-event data requires the cookie token.
    cookie = settings.cursor_session_token.strip()
    if cookie:
        try:
            events = cached(
                "cursor:events", ttl, lambda: _fetch_events_cookie(cookie, settings)
            )
            if events:
                daily, by_model = _aggregate_events(events, settings.history_days)
                snap.daily = daily
                snap.by_model = by_model
                snap.recent_events = sorted(
                    events, key=lambda e: e.timestamp, reverse=True
                )[: settings.recent_events_limit]
                snap.estimated_total_cost = sum(e.cost_usd for e in events)
                snap.available = True
                if not plan_ok and not snap.plan.plan_name:
                    snap.plan = PlanStatus(plan_name="Cursor")
        except requests.RequestException as exc:
            if not snap.available:
                snap.error = f"Cursor cookie API failed: {exc}"

    if not snap.available and not snap.error:
        snap.error = (
            "No Cursor credentials found. Sign in to Cursor desktop, or paste a "
            "WorkosCursorSessionToken cookie in Settings."
        )
    return snap
