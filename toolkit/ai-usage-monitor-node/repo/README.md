# AI Usage Monitor

A Windows 11 desktop GUI that shows **Cursor** and **Claude Code** token usage
and cost data side by side. Local-first and read-only: your data never leaves
your machine (it only talks to the official Cursor / Anthropic APIs).

![overview](docs/overview.png) <!-- placeholder -->

## What it shows

| | Cursor | Claude Code |
|---|---|---|
| Plan & billing cycle | ✅ (auto-detected from desktop login) | plan tier shown when available |
| Included limit vs spend | ✅ real $ (cents) | local estimate |
| Auto / API usage % | ✅ | – |
| On-demand spend | ✅ | – |
| Daily token/cost chart | ✅ (with session token) | ✅ |
| Per-model breakdown | ✅ (with session token) | ✅ |
| Recent requests | ✅ (with session token) | ✅ |

## Data sources

- **Cursor**
  - *Auto:* reads the JWT access token from Cursor desktop's local store
    (`%APPDATA%\Cursor\User\globalStorage\state.vscdb`) and calls the dashboard
    service (`api2.cursor.sh`). No manual setup if you're signed in to Cursor.
  - *Detailed events (optional):* paste a `WorkosCursorSessionToken` cookie in
    Settings to pull per-request model/token/cost data from `cursor.com`.
- **Claude Code**
  - Parses local session logs in `%USERPROFILE%\.claude\projects\**\*.jsonl`
    (and `~/.config/claude/projects`). Aggregates by day and model; cost is
    **estimated** from a local price table. Override the path in Settings or via
    `CLAUDE_CONFIG_DIR`.

> ⚠️ The Cursor endpoints are unofficial/reverse-engineered and may change
> without notice. Claude Pro/Max dollar figures are local estimates and may
> differ from your actual bill.

## Requirements

- **Windows 11** (also runs on macOS/Linux for development)
- **Python 3.10+**

## Run from source

```powershell
# In the project folder
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

## Terminal dashboard (works in WSL / Linux / macOS)

A colored terminal view that shows, per provider, **cost used this month /
billing cycle**, usage bars, **quota reset countdown**, and token + per-model
breakdown. No GUI/display required, so it runs directly in a WSL shell.

```bash
# from the project folder
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

./usage                 # pretty, colored (one-shot)
./usage --watch         # live, auto-refresh every 60s (Ctrl-C to quit)
./usage --watch 10      # refresh display every 10s
./usage --no-color      # plain text
./usage --json          # machine-readable
# equivalent: python -m ai_usage_monitor.cli
```

### Refresh interval — what to pick

The display refresh rate is decoupled from how often the (rate-limited) network
APIs are actually called:

- **Display** redraws every `--watch SECONDS` (local token data is re-read each
  time — cheap).
- **Network calls** (Cursor dashboard RPC, Claude OAuth usage) are cached and
  hit at most once per `api_min_interval_seconds` (default **60s**). So even
  `--watch 10` is safe and will not trigger Claude's `429` rate limit.

Recommendation: **30–60s** is the sweet spot — the underlying usage numbers
don't change meaningfully faster than that. Use `--watch 10` only if you want a
snappier clock/countdown; the API figures still update on the 60s cycle. Tune
the API cycle with `--api-interval SECONDS` if needed.

Example:

```
AI Usage  ·  Thu Jun 11 15:12

┌ Cursor — Team ───────────────────────────────────────
  This cycle    $49.41  (incl $20.00 + bonus $29.41)
  Included      [██████████████████████] 100%  $20.00 limit
  Auto / API    Auto 0%  ·  API 100%
  On-demand     $27.52
  Resets        19d 7h  →  2026-06-30 23:12  (billing cycle)

┌ Claude Team plan ────────────────────────────────────
  Session
    Duration    74h 13m  (wall)
    Usage       104,708 input, 808,469 output, 225,486,152 cache read, 6,267,771 cache write

  Current session
  [█████████████░░░░░░░░░░░░░░░░░░░░░] 39%   resets 7:19pm (Asia/Seoul)
  Current week (all models)
  [████████████░░░░░░░░░░░░░░░░░░░░░░] 36%   resets Jun 13, 7:59am (Asia/Seoul)

  Tokens        271.8M  · 1451 requests across 3 models (last 30d est.)
  Top models    opus-4-8 93.7%  ·  haiku-4-5 3.4%  ·  sonnet-4-6 3.0%
```

The Claude section mirrors Claude Code's own `/usage` command: a **Session**
block (wall duration, token usage) plus **Current session (5h)** and **Current
week** utilization bars with reset times in your local timezone.

> Claude has no real per-token bill (it's a flat subscription), so the tool does
> **not** show dollar estimates for Claude. "Top models" is shown as each
> model's **share of total tokens**. Dollar figures are reserved for Cursor,
> where they are real billing amounts.

### How it gets data in WSL

- **Cursor:** reads the Cursor **CLI** token from `~/.config/cursor/auth.json`
  (created when you sign in with `cursor-agent`) and calls the dashboard API,
  refreshing the token automatically when it expires. No desktop app needed.
- **Claude Code:**
  - *Rolling windows* (Current session / Current week %, reset times) come from
    the same authoritative OAuth endpoint Claude Code's `/usage` uses
    (`api.anthropic.com/api/oauth/usage`), via the token in
    `~/.claude/.credentials.json` (auto-refreshed on expiry). These reflect
    **all devices**, not just this machine.
  - *Session block, token totals, monthly cost, per-model breakdown* are parsed
    locally from `~/.claude/projects/**/*.jsonl`; cost is estimated from the
    local price table. If the OAuth endpoint is unavailable (e.g. 429 rate
    limit), it falls back to a local 5-hour block estimate.

> Note: the OAuth usage endpoint is beta and shared with running Claude Code
> sessions' polling, so it can occasionally return HTTP 429 — the tool degrades
> gracefully and shows the local estimate instead.

> Tip: add `alias usage='/path/to/ai-usage-monitor/usage'` to your `~/.bashrc`.

## Build a standalone .exe (Windows)

```powershell
pip install -r requirements-dev.txt
pyinstaller --noconfirm --windowed --name "AI Usage Monitor" run.py
# Output: dist\AI Usage Monitor\AI Usage Monitor.exe
```

## Settings

Stored at `%APPDATA%\ai-usage-monitor\settings.json`:

| Setting | Purpose |
|---|---|
| Auto-refresh interval | seconds between refreshes (0 = off) |
| History window | days of history to chart/aggregate |
| Show cost | toggle $ figures |
| Cursor session token | optional cookie for detailed events |
| Claude config dir | override JSONL location |
| Cursor Admin API key | optional (Enterprise; reserved for future) |

## Project layout

```
ai_usage_monitor/
  models.py            # shared dataclasses
  pricing.py           # local model price table + cost estimator
  config.py            # settings + platform data paths
  service.py           # runs both providers concurrently
  cli.py               # headless text/JSON report
  app.py               # GUI bootstrap
  providers/
    cursor_provider.py # SQLite token + dashboard API + cookie fallback
    claude_provider.py # JSONL parser + aggregation
  ui/                  # PySide6 widgets, charts, panels, settings
tests/                 # unit tests (pytest)
```

## Development

```bash
pip install -r requirements-dev.txt
QT_QPA_PLATFORM=offscreen pytest -q   # run tests headless
```

## Privacy & security

- All processing is local. The app reads local files and calls only the
  official Cursor/Anthropic endpoints.
- Tokens are stored in the local settings file. Treat that file as a secret.
  (A future version can move secrets to Windows Credential Manager.)

## Roadmap

- System tray + Windows toast alerts at 80%/90% usage
- Claude OAuth plan-limit bars (5h / weekly windows)
- Cursor Enterprise Admin API (team spend) support
- SQLite history snapshots for long-term trends
