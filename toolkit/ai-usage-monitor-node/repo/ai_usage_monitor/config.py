"""Configuration, settings persistence, and platform-specific data paths."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path


def _appdata_dir() -> Path:
    """Roaming app-data directory (Windows: %APPDATA%, else ~/.config)."""
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata)
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg)
    return Path.home() / ".config"


def settings_path() -> Path:
    return _appdata_dir() / "ai-usage-monitor" / "settings.json"


def cursor_token_files() -> list[Path]:
    """Candidate JSON files holding the Cursor CLI access/refresh tokens.

    The Cursor CLI (``cursor-agent``) stores ``{accessToken, refreshToken}`` in
    ``~/.config/cursor/auth.json`` on Linux/WSL. This is what makes the
    dashboard API reachable from WSL without the desktop app.
    """
    candidates: list[Path] = []
    xdg = os.environ.get("XDG_CONFIG_HOME")
    home = Path.home()
    if xdg:
        candidates.append(Path(xdg) / "cursor" / "auth.json")
    candidates.append(home / ".config" / "cursor" / "auth.json")
    candidates.append(home / ".cursor" / "auth.json")
    userprofile = os.environ.get("USERPROFILE")
    if userprofile:
        candidates.append(Path(userprofile) / ".config" / "cursor" / "auth.json")
        candidates.append(Path(userprofile) / ".cursor" / "auth.json")
    # De-dup preserving order.
    seen: set[Path] = set()
    out: list[Path] = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def cursor_state_db_paths() -> list[Path]:
    """Candidate locations of Cursor's globalStorage SQLite DB."""
    candidates: list[Path] = []
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(
            Path(appdata) / "Cursor" / "User" / "globalStorage" / "state.vscdb"
        )
    # macOS / Linux fallbacks (useful for dev on WSL/macOS)
    home = Path.home()
    candidates.append(
        home
        / "Library"
        / "Application Support"
        / "Cursor"
        / "User"
        / "globalStorage"
        / "state.vscdb"
    )
    candidates.append(
        home / ".config" / "Cursor" / "User" / "globalStorage" / "state.vscdb"
    )
    return [c for c in candidates if c.exists()] or candidates


def claude_project_dirs(override: str | None = None) -> list[Path]:
    """Directories that contain Claude Code session JSONL files.

    Honors CLAUDE_CONFIG_DIR (comma-separated) and the explicit settings
    override, then falls back to the standard new/legacy locations.
    """
    dirs: list[Path] = []

    def add(root: Path) -> None:
        proj = root / "projects" if root.name != "projects" else root
        if proj not in dirs:
            dirs.append(proj)

    raw = override or os.environ.get("CLAUDE_CONFIG_DIR", "")
    if raw.strip():
        # An explicit override (settings or CLAUDE_CONFIG_DIR) replaces the
        # default search roots entirely, matching Claude Code / ccusage behavior.
        for part in (p.strip() for p in raw.split(",")):
            if part:
                add(Path(part).expanduser())
    else:
        home = Path.home()
        userprofile = os.environ.get("USERPROFILE")
        roots = [home / ".config" / "claude", home / ".claude"]
        if userprofile:
            roots += [
                Path(userprofile) / ".claude",
                Path(userprofile) / ".config" / "claude",
            ]
        for r in roots:
            add(r)

    # De-dup while keeping order; only return ones that exist for scanning.
    seen: set[Path] = set()
    out: list[Path] = []
    for d in dirs:
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out


def claude_credentials_files() -> list[Path]:
    """Candidate locations of Claude Code's OAuth credentials file."""
    candidates: list[Path] = []
    home = Path.home()
    candidates.append(home / ".claude" / ".credentials.json")
    candidates.append(home / ".config" / "claude" / ".credentials.json")
    userprofile = os.environ.get("USERPROFILE")
    if userprofile:
        candidates.append(Path(userprofile) / ".claude" / ".credentials.json")
    seen: set[Path] = set()
    out: list[Path] = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


@dataclass
class Settings:
    refresh_interval_seconds: int = 300
    # Minimum seconds between actual network calls to rate-limited endpoints
    # (Cursor RPC, Claude OAuth usage). The display may refresh faster than this;
    # API results are cached in between to avoid 429s.
    api_min_interval_seconds: int = 60
    show_cost: bool = True
    cursor_session_token: str = ""  # manual WorkosCursorSessionToken fallback
    claude_config_dir: str = ""  # manual override for JSONL location
    cursor_admin_api_key: str = ""  # optional Enterprise Admin API
    recent_events_limit: int = 50
    history_days: int = 30

    @classmethod
    def load(cls) -> "Settings":
        path = settings_path()
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                known = {k: v for k, v in data.items() if k in cls.__annotations__}
                return cls(**known)
            except Exception:
                pass
        return cls()

    def save(self) -> None:
        path = settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
