"""Headless terminal dashboard for Cursor and Claude usage.

Designed to run in any terminal (incl. WSL). Shows, per provider:
  * cost used this month / billing cycle
  * usage bars and percentages (where available)
  * quota reset countdown (Cursor billing cycle, Claude 5h block)
  * token usage and a per-model cost breakdown

Usage:
    python -m ai_usage_monitor.cli            # pretty, colored
    python -m ai_usage_monitor.cli --json     # machine-readable
    python -m ai_usage_monitor.cli --no-color # plain text
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone

from .config import Settings
from .models import PlanStatus, ProviderSnapshot
from .service import load_dashboard

# --- ANSI helpers -----------------------------------------------------------

_USE_COLOR = True


def _supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return sys.stdout.isatty()


class C:
    RESET = "\033[0m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    CYAN = "\033[36m"
    BLUE = "\033[34m"
    ORANGE = "\033[38;5;209m"
    GREY = "\033[38;5;245m"


def _c(text: str, *codes: str) -> str:
    if not _USE_COLOR or not codes:
        return text
    return "".join(codes) + text + C.RESET


# --- formatting helpers -----------------------------------------------------


def _usd(v) -> str:
    return "-" if v is None else f"${v:,.2f}"


def _tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def _pct_color(p: float) -> str:
    if p >= 90:
        return C.RED
    if p >= 75:
        return C.YELLOW
    return C.GREEN


def _bar(percent: float | None, width: int = 22) -> str:
    if percent is None:
        return _c("[" + "·" * width + "] n/a", C.GREY)
    pct = max(0.0, min(100.0, percent))
    filled = int(round(width * pct / 100.0))
    bar = "█" * filled + "░" * (width - filled)
    return _c("[", C.GREY) + _c(bar, _pct_color(pct)) + _c("]", C.GREY) + f" {pct:.0f}%"


def _countdown(reset_at: float | None) -> str:
    if not reset_at:
        return "-"
    now = datetime.now(timezone.utc).timestamp()
    delta = int(reset_at - now)
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


def _reset_date(reset_at: float | None) -> str:
    if not reset_at:
        return ""
    return datetime.fromtimestamp(reset_at).strftime("%Y-%m-%d %H:%M")


def _local_tzname() -> str:
    tz = os.environ.get("TZ")
    if tz:
        return tz
    try:
        with open("/etc/timezone", encoding="utf-8") as fh:
            name = fh.read().strip()
            if name:
                return name
    except OSError:
        pass
    return datetime.now().astimezone().tzname() or "local"


def _fmt_clock(dt: datetime) -> str:
    hour12 = dt.hour % 12 or 12
    ampm = "am" if dt.hour < 12 else "pm"
    return f"{hour12}:{dt.minute:02d}{ampm}"


def _reset_local(reset_at: float | None) -> str:
    """Mirror Claude /usage: 'Resets 7:19pm (Asia/Seoul)' / 'Jun 13, 7:59am ...'."""
    if not reset_at:
        return "-"
    dt = datetime.fromtimestamp(reset_at)
    now = datetime.now()
    clock = _fmt_clock(dt)
    if dt.date() != now.date():
        clock = f"{dt.strftime('%b')} {dt.day}, {clock}"
    return f"{clock} ({_local_tzname()})"


def _fmt_duration(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}h {m}m"
    if m:
        return f"{m}m {sec}s"
    return f"{sec}s"


def _header(title: str, color: str) -> str:
    line = "─" * max(4, 52 - len(title))
    return _c(f"┌ {title} ", C.BOLD, color) + _c(line, C.GREY)


def _row(label: str, value: str) -> str:
    return f"  {_c(label.ljust(13), C.GREY)} {value}"


# --- rendering --------------------------------------------------------------


def _render_cursor(snap: ProviderSnapshot, show_cost: bool) -> list[str]:
    out = []
    if not snap.available:
        out.append(_header("Cursor", C.BLUE))
        out.append(_c(f"  {snap.error}", C.GREY))
        return out
    p: PlanStatus = snap.plan
    out.append(_header(f"Cursor — {p.plan_name}", C.BLUE))

    if show_cost and p.month_cost_usd is not None:
        extra = ""
        if p.bonus_usd:
            incl = (p.month_cost_usd or 0) - p.bonus_usd
            extra = _c(f"  (incl {_usd(incl)} + bonus {_usd(p.bonus_usd)})", C.GREY)
        out.append(_row("This cycle", _c(_usd(p.month_cost_usd), C.BOLD) + extra))

    if p.used_percent is not None:
        limit = f"  {_usd(p.limit_usd)} limit" if p.limit_usd is not None else ""
        out.append(_row("Included", _bar(p.used_percent) + _c(limit, C.GREY)))
    if p.auto_percent is not None or p.api_percent is not None:
        a = "-" if p.auto_percent is None else f"{p.auto_percent:.0f}%"
        api = "-" if p.api_percent is None else f"{p.api_percent:.0f}%"
        out.append(_row("Auto / API", _c(f"Auto {a}  ·  API {api}", C.GREY)))
    if show_cost and p.on_demand_usd is not None:
        out.append(_row("On-demand", _usd(p.on_demand_usd)))

    if p.reset_at:
        when = _c(_countdown(p.reset_at), C.CYAN)
        date = _c(f"→  {_reset_date(p.reset_at)}  ({p.reset_label})", C.GREY)
        out.append(_row("Resets", f"{when}  {date}"))

    if snap.by_model and show_cost:
        out.append(_model_line(snap))
    return out


def _render_claude(snap: ProviderSnapshot, show_cost: bool) -> list[str]:
    out = []
    if not snap.available:
        out.append(_header("Claude Code", C.ORANGE))
        out.append(_c(f"  {snap.error}", C.GREY))
        return out
    p = snap.plan
    out.append(_header(p.plan_name, C.ORANGE))

    # --- Session block (mirrors /usage "Session") ---
    sess = snap.session
    if sess is not None:
        out.append("  " + _c("Session", C.BOLD))
        out.append(_row("  Duration", _fmt_duration(sess.wall_seconds) + _c("  (wall)", C.GREY)))
        t = sess.tokens
        out.append(
            _row(
                "  Usage",
                _c(
                    f"{t.input_tokens:,} input, {t.output_tokens:,} output, "
                    f"{t.cache_read_tokens:,} cache read, "
                    f"{t.cache_creation_tokens:,} cache write",
                    C.GREY,
                ),
            )
        )
        out.append("")

    # --- Rolling windows (authoritative from OAuth usage API) ---
    if snap.rate_windows:
        for w in snap.rate_windows:
            out.append("  " + _c(w.name, C.BOLD))
            reset = _c(f"resets {_reset_local(w.resets_at)}", C.CYAN)
            out.append(f"  {_bar(w.utilization, width=34)}   {reset}")
    else:
        # Fall back to the local 5h-block estimate when the API is unavailable.
        if p.reset_at:
            out.append("  " + _c("Current session (local est.)", C.BOLD))
            block = f"{_usd(p.block_cost_usd)}  ·  " if show_cost else ""
            out.append(
                f"  {block}" + _c(f"resets in {_countdown(p.reset_at)}", C.CYAN)
            )

    # --- Token summary + per-model share (no cost: all Claude figures are est.) ---
    out.append("")
    total_tokens = sum(m.tokens.total for m in snap.by_model)
    out.append(_row("Tokens", f"{_tokens(total_tokens)}  " + _c(f"· {p.message}", C.GREY)))
    if snap.by_model:
        out.append(_model_line(snap, as_percent=True))
    return out


def _model_line(snap: ProviderSnapshot, as_percent: bool = False) -> str:
    bits = []
    if as_percent:
        total = sum(m.tokens.total for m in snap.by_model) or 1
        ranked = sorted(snap.by_model, key=lambda m: m.tokens.total, reverse=True)
        for m in ranked[:4]:
            short = m.model.replace("claude-", "").replace("-high-thinking", "")
            bits.append(f"{short} {m.tokens.total / total * 100:.1f}%")
    else:
        for m in snap.by_model[:4]:
            short = m.model.replace("claude-", "").replace("-high-thinking", "")
            bits.append(f"{short} {_usd(m.cost_usd)}")
    return _row("Top models", _c("  ·  ".join(bits), C.GREY))


def _snapshot_to_dict(snap: ProviderSnapshot) -> dict:
    d = asdict(snap)
    for day in d.get("daily", []):
        day["day"] = str(day["day"])
    return d


def _render_all(settings: Settings, note: str = "") -> None:
    data = load_dashboard(settings)
    stamp = datetime.now().strftime("%a %b %d %H:%M:%S")
    print(_c("AI Usage", C.BOLD) + _c(f"  ·  {stamp}{note}", C.GREY))
    print()
    for line in _render_cursor(data.cursor, settings.show_cost):
        print(line)
    print()
    for line in _render_claude(data.claude, settings.show_cost):
        print(line)
    print()


def main() -> int:
    global _USE_COLOR
    parser = argparse.ArgumentParser(description="AI usage terminal dashboard")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--no-color", action="store_true", help="disable ANSI color")
    parser.add_argument(
        "-w",
        "--watch",
        nargs="?",
        const=60,
        type=int,
        metavar="SECONDS",
        help="auto-refresh every SECONDS (default 60). Display refreshes at this "
        "rate; network calls are throttled by api_min_interval_seconds.",
    )
    parser.add_argument(
        "--api-interval",
        type=int,
        default=None,
        metavar="SECONDS",
        help="minimum seconds between network API calls (default 60)",
    )
    args = parser.parse_args()

    _USE_COLOR = _supports_color() and not args.no_color

    settings = Settings.load()
    if args.api_interval is not None:
        settings.api_min_interval_seconds = max(0, args.api_interval)

    if args.json:
        data = load_dashboard(settings)
        print(
            json.dumps(
                {
                    "cursor": _snapshot_to_dict(data.cursor),
                    "claude": _snapshot_to_dict(data.claude),
                },
                indent=2,
                default=str,
            )
        )
        return 0

    if args.watch is None:
        _render_all(settings)
        return 0

    interval = max(1, args.watch)
    # Keep API calls safe even with a tiny display interval.
    if interval < settings.api_min_interval_seconds and args.api_interval is None:
        pass  # cache already throttles network calls to api_min_interval_seconds
    note = f"   (every {interval}s · API cache {settings.api_min_interval_seconds}s · Ctrl-C to quit)"
    try:
        while True:
            # Clear screen + home cursor.
            if _USE_COLOR:
                sys.stdout.write("\033[2J\033[H")
            _render_all(settings, note=note)
            sys.stdout.flush()
            time.sleep(interval)
    except KeyboardInterrupt:
        print()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
