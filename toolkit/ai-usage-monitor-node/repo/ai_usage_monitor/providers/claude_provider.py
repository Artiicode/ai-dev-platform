"""Claude Code provider.

Reads Claude Code's local session JSONL files and aggregates token usage and
estimated cost by day and by model. 100% local and read-only.

File layout: <config>/projects/<project>/**/<sessionId>.jsonl
Each assistant message line carries `message.usage` with token counts.
"""

from __future__ import annotations

import json
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator

import requests

from ..cache import cached
from ..config import Settings, claude_credentials_files, claude_project_dirs
from ..models import (
    DailyUsage,
    ModelUsage,
    PlanStatus,
    ProviderSnapshot,
    RateWindow,
    SessionBlock,
    TokenBreakdown,
    UsageEvent,
)
from ..pricing import estimate_cost

_OAUTH_USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
_OAUTH_TOKEN_URL = "https://platform.claude.com/v1/oauth/token"
_OAUTH_CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
_OAUTH_BETA = "oauth-2025-04-20"
_USER_AGENT = "claude-code/2.0.32"


def _iter_jsonl_files(dirs: Iterable[Path]) -> Iterator[Path]:
    for d in dirs:
        if d.exists():
            yield from d.rglob("*.jsonl")


def _parse_timestamp(value: str) -> float | None:
    if not value:
        return None
    try:
        # Handle trailing Z and fractional seconds.
        ts = value.replace("Z", "+00:00")
        return datetime.fromisoformat(ts).timestamp()
    except ValueError:
        return None


def _extract_usage(line: str) -> tuple[str, str, str, dict, str] | None:
    """Return (dedupe_key, model, timestamp_str, usage, session_id)."""
    try:
        rec = json.loads(line)
    except (json.JSONDecodeError, ValueError):
        return None
    if rec.get("type") != "assistant":
        return None
    msg = rec.get("message")
    if not isinstance(msg, dict):
        return None
    usage = msg.get("usage")
    if not isinstance(usage, dict):
        return None
    model = msg.get("model") or "unknown"
    if model == "<synthetic>":
        # Synthetic assistant messages carry no real billing.
        return None
    msg_id = msg.get("id") or ""
    req_id = rec.get("requestId") or ""
    dedupe_key = f"{msg_id}:{req_id}" if (msg_id or req_id) else ""
    ts = rec.get("timestamp", "")
    session_id = rec.get("sessionId") or ""
    return dedupe_key, model, ts, usage, session_id


def collect_events(settings: Settings) -> list[UsageEvent]:
    """Parse all JSONL files into deduplicated UsageEvents."""
    dirs = claude_project_dirs(settings.claude_config_dir or None)
    seen_keys: set[str] = set()
    events: list[UsageEvent] = []

    for path in _iter_jsonl_files(dirs):
        try:
            with path.open("r", encoding="utf-8", errors="replace") as fh:
                file_session = path.stem
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    parsed = _extract_usage(line)
                    if parsed is None:
                        continue
                    dedupe_key, model, ts_str, usage, rec_session = parsed
                    session_id = rec_session or file_session
                    if dedupe_key:
                        if dedupe_key in seen_keys:
                            continue
                        seen_keys.add(dedupe_key)

                    tokens = TokenBreakdown(
                        input_tokens=int(usage.get("input_tokens", 0) or 0),
                        output_tokens=int(usage.get("output_tokens", 0) or 0),
                        cache_read_tokens=int(
                            usage.get("cache_read_input_tokens", 0) or 0
                        ),
                        cache_creation_tokens=int(
                            usage.get("cache_creation_input_tokens", 0) or 0
                        ),
                    )
                    if tokens.total == 0:
                        continue
                    ts = _parse_timestamp(ts_str)
                    cost = estimate_cost(
                        model,
                        tokens.input_tokens,
                        tokens.output_tokens,
                        tokens.cache_read_tokens,
                        tokens.cache_creation_tokens,
                    )
                    events.append(
                        UsageEvent(
                            timestamp=ts or 0.0,
                            model=model,
                            tokens=tokens,
                            cost_usd=cost,
                            source="claude",
                            session_id=session_id,
                        )
                    )
        except OSError:
            continue
    return events


def aggregate(events: list[UsageEvent], history_days: int) -> tuple[
    list[DailyUsage], list[ModelUsage], float
]:
    daily: "OrderedDict[object, DailyUsage]" = OrderedDict()
    by_model: dict[str, ModelUsage] = {}
    total_cost = 0.0

    now = datetime.now(timezone.utc).timestamp()
    cutoff = now - history_days * 86400 if history_days > 0 else 0

    for ev in events:
        total_cost += ev.cost_usd
        if ev.timestamp and ev.timestamp >= cutoff:
            day = datetime.fromtimestamp(ev.timestamp, tz=timezone.utc).date()
            bucket = daily.get(day)
            if bucket is None:
                bucket = DailyUsage(day=day)
                daily[day] = bucket
            bucket.tokens += ev.tokens
            bucket.cost_usd += ev.cost_usd
            bucket.events += 1

        mu = by_model.get(ev.model)
        if mu is None:
            mu = ModelUsage(model=ev.model)
            by_model[ev.model] = mu
        mu.tokens += ev.tokens
        mu.cost_usd += ev.cost_usd
        mu.events += 1

    daily_list = sorted(daily.values(), key=lambda d: d.day)
    model_list = sorted(by_model.values(), key=lambda m: m.cost_usd, reverse=True)
    return daily_list, model_list, total_cost


_BLOCK_SECONDS = 5 * 3600  # Claude's 5-hour billing window


def month_cost(events: list[UsageEvent], now: datetime | None = None) -> float:
    """Estimated cost for events in the current local calendar month."""
    now = now or datetime.now()
    total = 0.0
    for ev in events:
        if not ev.timestamp:
            continue
        dt = datetime.fromtimestamp(ev.timestamp)  # local time
        if dt.year == now.year and dt.month == now.month:
            total += ev.cost_usd
    return total


def active_block(events: list[UsageEvent], now_ts: float | None = None):
    """Return (block_cost, block_tokens, reset_at) for the active 5h block.

    Mirrors ccusage block logic: a block starts at the first entry (floored to
    the hour) and ends 5h later, or earlier if there is a >5h gap between
    entries. The active block is the latest one that still contains `now`.
    """
    timed = sorted((e for e in events if e.timestamp), key=lambda e: e.timestamp)
    if not timed:
        return 0.0, 0, None
    now_ts = now_ts if now_ts is not None else datetime.now(timezone.utc).timestamp()

    block_start = (int(timed[0].timestamp) // 3600) * 3600
    last_ts = timed[0].timestamp
    cost = 0.0
    tokens = 0
    for ev in timed:
        if (ev.timestamp - block_start >= _BLOCK_SECONDS) or (
            ev.timestamp - last_ts >= _BLOCK_SECONDS
        ):
            block_start = (int(ev.timestamp) // 3600) * 3600
            cost = 0.0
            tokens = 0
        cost += ev.cost_usd
        tokens += ev.tokens.total
        last_ts = ev.timestamp

    reset_at = block_start + _BLOCK_SECONDS
    if now_ts >= reset_at:
        # Most recent block already elapsed; no active block right now.
        return 0.0, 0, None
    return cost, tokens, reset_at


def latest_session_block(events: list[UsageEvent]) -> SessionBlock | None:
    """Build a SessionBlock for the most recently active session id."""
    timed = [e for e in events if e.timestamp]
    if not timed:
        return None
    # Identify the session whose last activity is the most recent.
    last_by_session: dict[str, float] = {}
    for e in timed:
        sid = e.session_id or "?"
        if e.timestamp > last_by_session.get(sid, 0):
            last_by_session[sid] = e.timestamp
    current = max(last_by_session, key=last_by_session.get)

    block = SessionBlock(session_id=current)
    first_ts = None
    last_ts = None
    for e in timed:
        if (e.session_id or "?") != current:
            continue
        block.cost_usd += e.cost_usd
        block.tokens += e.tokens
        block.requests += 1
        first_ts = e.timestamp if first_ts is None else min(first_ts, e.timestamp)
        last_ts = e.timestamp if last_ts is None else max(last_ts, e.timestamp)
    if first_ts is not None and last_ts is not None:
        block.wall_seconds = max(0.0, last_ts - first_ts)
    return block


def _read_credentials() -> tuple[dict | None, Path | None]:
    for path in claude_credentials_files():
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data.get("claudeAiOauth"), dict):
            return data, path
    return None, None


def _refresh_oauth(creds: dict, path: Path | None) -> str | None:
    oauth = creds.get("claudeAiOauth", {})
    refresh = oauth.get("refreshToken")
    if not refresh:
        return None
    try:
        resp = requests.post(
            _OAUTH_TOKEN_URL,
            json={
                "grant_type": "refresh_token",
                "client_id": _OAUTH_CLIENT_ID,
                "refresh_token": refresh,
            },
            headers={"User-Agent": _USER_AGENT},
            timeout=20,
        )
        resp.raise_for_status()
        body = resp.json()
    except (requests.RequestException, ValueError):
        return None
    new_access = body.get("access_token")
    if not new_access:
        return None
    oauth["accessToken"] = new_access
    if body.get("refresh_token"):
        oauth["refreshToken"] = body["refresh_token"]
    if body.get("expires_in"):
        oauth["expiresAt"] = int(
            (datetime.now(timezone.utc).timestamp() + body["expires_in"]) * 1000
        )
    if path is not None:
        try:
            path.write_text(json.dumps(creds), encoding="utf-8")
        except OSError:
            pass
    return new_access


def _request_oauth_usage(token: str) -> requests.Response:
    return requests.get(
        _OAUTH_USAGE_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "anthropic-beta": _OAUTH_BETA,
            "User-Agent": _USER_AGENT,
            "Accept": "application/json",
        },
        timeout=20,
    )


_WINDOW_LABELS = {
    "five_hour": "Current session",
    "seven_day": "Current week (all models)",
    "seven_day_sonnet": "Current week (Sonnet)",
    "seven_day_opus": "Current week (Opus)",
}


def fetch_rate_windows(settings: Settings) -> tuple[list[RateWindow], str]:
    """Cached wrapper around the OAuth usage fetch (avoids 429 under fast refresh)."""
    return cached(
        "claude:rate_windows",
        max(0, settings.api_min_interval_seconds),
        lambda: _fetch_rate_windows_uncached(settings),
    )


def _fetch_rate_windows_uncached(settings: Settings) -> tuple[list[RateWindow], str]:
    """Fetch Claude rolling rate-limit windows via the OAuth usage endpoint.

    Returns (windows, error). On 401 it refreshes the token once and retries.
    """
    creds, path = _read_credentials()
    if not creds:
        return [], "No Claude OAuth credentials found (~/.claude/.credentials.json)."
    token = creds["claudeAiOauth"].get("accessToken")
    if not token:
        return [], "Claude credentials present but no access token."

    try:
        resp = _request_oauth_usage(token)
        if resp.status_code in (401, 403):
            new_token = _refresh_oauth(creds, path)
            if new_token:
                resp = _request_oauth_usage(new_token)
        if resp.status_code == 429:
            return [], "Claude usage endpoint rate-limited (429); try again shortly."
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as exc:
        return [], f"Claude usage fetch failed: {exc}"

    windows: list[RateWindow] = []
    for key, label in _WINDOW_LABELS.items():
        win = data.get(key)
        if not isinstance(win, dict):
            continue
        util = win.get("utilization")
        if util is None:
            continue
        resets_at = _parse_timestamp(win.get("resets_at", "")) if win.get("resets_at") else None
        windows.append(RateWindow(name=label, utilization=float(util), resets_at=resets_at))
    return windows, ""


def get_snapshot(settings: Settings) -> ProviderSnapshot:
    snap = ProviderSnapshot(source="claude", is_estimated_cost=True)
    try:
        events = collect_events(settings)
    except Exception as exc:  # pragma: no cover - defensive
        snap.error = f"Failed to read Claude data: {exc}"
        return snap

    if not events:
        snap.error = (
            "No Claude Code usage found. Checked: "
            + ", ".join(str(p) for p in claude_project_dirs(
                settings.claude_config_dir or None
            ))
        )
        return snap

    daily, by_model, total_cost = aggregate(events, settings.history_days)
    snap.available = True
    snap.daily = daily
    snap.by_model = by_model
    snap.estimated_total_cost = total_cost
    snap.recent_events = sorted(
        events, key=lambda e: e.timestamp, reverse=True
    )[: settings.recent_events_limit]
    snap.session = latest_session_block(events)

    # Server-side rolling windows (authoritative, cross-device) for the
    # /usage-style "Current session" / "Current week" bars.
    windows, win_err = fetch_rate_windows(settings)
    snap.rate_windows = windows

    # Plan card. Subscription tier comes from the OAuth credentials when present.
    creds, _ = _read_credentials()
    sub = (creds or {}).get("claudeAiOauth", {}).get("subscriptionType", "") if creds else ""
    plan_name = f"Claude {sub.capitalize()} plan" if sub else "Claude Code (local)"
    plan = PlanStatus(plan_name=plan_name)
    plan.spend_usd = round(sum(d.cost_usd for d in daily), 2)
    plan.month_cost_usd = round(month_cost(events), 2)
    block_cost, _block_tokens, reset_at = active_block(events)
    if reset_at is not None:
        plan.reset_at = reset_at
        plan.reset_label = "5h block"
        plan.block_cost_usd = round(block_cost, 2)
    plan.message = (
        f"{len(events)} requests across {len(by_model)} models "
        f"(last {settings.history_days}d est.)"
    )
    snap.plan = plan
    return snap
