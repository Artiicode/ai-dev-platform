import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_usage_monitor.config import Settings  # noqa: E402
from ai_usage_monitor.providers import claude_provider  # noqa: E402


def _write_jsonl(path, records):
    with open(path, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")


def _assistant(msg_id, req_id, model, usage, ts):
    return {
        "type": "assistant",
        "requestId": req_id,
        "timestamp": ts,
        "message": {"id": msg_id, "model": model, "usage": usage},
    }


def test_parse_and_dedupe(tmp_path):
    proj = tmp_path / "projects" / "demo"
    proj.mkdir(parents=True)
    usage = {
        "input_tokens": 10,
        "output_tokens": 100,
        "cache_read_input_tokens": 50,
        "cache_creation_input_tokens": 20,
    }
    # Two identical (msg_id+req_id) records -> counted once.
    recs = [
        _assistant("m1", "r1", "claude-sonnet-4-6", usage, "2026-06-10T10:00:00.000Z"),
        _assistant("m1", "r1", "claude-sonnet-4-6", usage, "2026-06-10T10:00:00.000Z"),
        _assistant("m2", "r2", "claude-opus-4", usage, "2026-06-10T11:00:00.000Z"),
        {"type": "user", "message": {"role": "user", "content": "hi"}},
    ]
    _write_jsonl(proj / "session1.jsonl", recs)

    settings = Settings(claude_config_dir=str(tmp_path), history_days=365)
    events = claude_provider.collect_events(settings)
    assert len(events) == 2  # deduped

    daily, by_model, total = claude_provider.aggregate(events, 365)
    assert len(by_model) == 2
    assert total > 0
    # one day
    assert len(daily) == 1
    assert daily[0].events == 2


def test_empty_dir(tmp_path):
    settings = Settings(claude_config_dir=str(tmp_path), history_days=30)
    snap = claude_provider.get_snapshot(settings)
    assert not snap.available
    assert "No Claude Code usage" in snap.error


def test_month_cost_and_active_block():
    from datetime import datetime, timezone

    from ai_usage_monitor.models import TokenBreakdown, UsageEvent

    now = datetime(2026, 6, 11, 12, 0, tzinfo=timezone.utc)
    now_ts = now.timestamp()

    def ev(offset_seconds, cost):
        return UsageEvent(
            timestamp=now_ts + offset_seconds,
            model="claude-sonnet-4-6",
            tokens=TokenBreakdown(output_tokens=100),
            cost_usd=cost,
            source="claude",
        )

    # Last month event + two recent events within a 5h block.
    last_month = UsageEvent(
        timestamp=datetime(2026, 5, 20, tzinfo=timezone.utc).timestamp(),
        model="claude-sonnet-4-6",
        tokens=TokenBreakdown(output_tokens=100),
        cost_usd=99.0,
        source="claude",
    )
    events = [last_month, ev(-3600, 1.0), ev(-600, 2.0)]

    mc = claude_provider.month_cost(events, now=datetime(2026, 6, 11, 12, 0))
    assert abs(mc - 3.0) < 1e-9  # excludes the May event

    cost, tokens, reset_at = claude_provider.active_block(events, now_ts=now_ts)
    assert abs(cost - 3.0) < 1e-9
    assert tokens == 200
    assert reset_at is not None and reset_at > now_ts


def test_no_active_block_when_idle():
    from datetime import datetime, timezone

    from ai_usage_monitor.models import TokenBreakdown, UsageEvent

    old = UsageEvent(
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp(),
        model="claude-sonnet-4-6",
        tokens=TokenBreakdown(output_tokens=100),
        cost_usd=1.0,
        source="claude",
    )
    now_ts = datetime(2026, 6, 11, tzinfo=timezone.utc).timestamp()
    cost, tokens, reset_at = claude_provider.active_block([old], now_ts=now_ts)
    assert reset_at is None


def test_latest_session_block():
    from datetime import datetime, timezone

    from ai_usage_monitor.models import TokenBreakdown, UsageEvent

    base = datetime(2026, 6, 11, tzinfo=timezone.utc).timestamp()

    def ev(sid, off, cost, out):
        return UsageEvent(
            timestamp=base + off,
            model="claude-sonnet-4-6",
            tokens=TokenBreakdown(output_tokens=out),
            cost_usd=cost,
            source="claude",
            session_id=sid,
        )

    events = [
        ev("old", 0, 5.0, 100),       # older session
        ev("cur", 1000, 1.0, 10),     # current session, two events
        ev("cur", 4600, 2.0, 20),
    ]
    block = claude_provider.latest_session_block(events)
    assert block.session_id == "cur"
    assert block.requests == 2
    assert abs(block.cost_usd - 3.0) < 1e-9
    assert block.tokens.output_tokens == 30
    assert abs(block.wall_seconds - 3600.0) < 1e-9


def test_fetch_rate_windows_parsing(monkeypatch):
    from ai_usage_monitor.config import Settings

    creds = {"claudeAiOauth": {"accessToken": "tok", "refreshToken": "r"}}
    monkeypatch.setattr(claude_provider, "_read_credentials", lambda: (creds, None))

    class FakeResp:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "five_hour": {"utilization": 38.0, "resets_at": "2026-06-11T10:20:00+00:00"},
                "seven_day": {"utilization": 36.0, "resets_at": "2026-06-12T23:00:00+00:00"},
                "seven_day_opus": None,
                "extra_usage": {"is_enabled": False},
            }

    monkeypatch.setattr(claude_provider, "_request_oauth_usage", lambda t: FakeResp())
    # ttl=0 disables caching so the producer always runs.
    windows, err = claude_provider.fetch_rate_windows(Settings(api_min_interval_seconds=0))
    assert err == ""
    assert len(windows) == 2
    assert windows[0].name == "Current session"
    assert windows[0].utilization == 38.0
    assert windows[0].resets_at is not None


def test_skips_zero_token_events(tmp_path):
    proj = tmp_path / "projects" / "demo"
    proj.mkdir(parents=True)
    zero = {"input_tokens": 0, "output_tokens": 0}
    _write_jsonl(
        proj / "s.jsonl",
        [_assistant("m1", "r1", "claude-sonnet-4-6", zero, "2026-06-10T10:00:00Z")],
    )
    settings = Settings(claude_config_dir=str(tmp_path), history_days=365)
    assert claude_provider.collect_events(settings) == []
