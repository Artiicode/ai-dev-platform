#!/usr/bin/env python3
"""mcp_launch — env-injecting exec shim for external MCP servers.

Loads the platform-root `.env` (gitignored secrets file) into the environment, then
execs the real MCP server command. This lets external-server credentials live ONLY in
`.env` — persistent, a single source — instead of being `export`ed every shell/reboot
or duplicated as plaintext into `.mcp.json`.

Usage:  mcp_launch.py -- <command> [args...]
"""
from __future__ import annotations
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_env(path):
    """Minimal .env parser (no dependency). KEY=VALUE per line; '#' comments and blanks
    ignored. Unquoted values drop an inline ' #...' comment; quote a value to keep '#'.
    Does NOT override a variable already set in the environment (an explicit export wins)."""
    if not os.path.exists(path):
        return
    for raw in open(path, encoding="utf-8", errors="replace"):
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip()
        if val[:1] in ("'", '"'):
            q = val[0]
            end = val.find(q, 1)
            val = val[1:end] if end > 0 else val[1:]
        else:
            val = re.split(r"\s+#", val, 1)[0].strip()
        if key and key not in os.environ:
            os.environ[key] = val


def main(argv):
    cmd = argv[argv.index("--") + 1:] if "--" in argv else argv
    if not cmd:
        sys.stderr.write("mcp_launch: no command after '--'\n")
        return 2
    _load_env(os.path.join(ROOT, ".env"))
    try:
        os.execvp(cmd[0], cmd)
    except FileNotFoundError:
        sys.stderr.write("mcp_launch: command not found: %s\n" % cmd[0])
        return 127


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
