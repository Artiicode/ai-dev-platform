#!/usr/bin/env bash
# Strip AI/tool attribution trailers from a commit message file (in place).
# See CONTRIBUTING.md — Co-Authored-By / Made-with / Generated with are forbidden.
set -euo pipefail

msg_file="${1:?usage: strip-ai-trailers.sh <commit-msg-file>}"
[ -f "$msg_file" ] || exit 0

python3 - "$msg_file" <<'PY'
import re, sys
from pathlib import Path
path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8", errors="replace")
lines = text.splitlines(keepends=True)
pat = re.compile(
    r"^\s*(Co-Authored-By|Co-authored-by|Made-with|Made-With)\s*:"
    r"|^\s*Generated with\s+",
    re.I,
)
kept = [ln for ln in lines if not pat.search(ln)]
# Trim trailing blank lines
while kept and kept[-1].strip() == "":
    kept.pop()
if kept and not kept[-1].endswith("\n"):
    kept[-1] += "\n"
new = "".join(kept)
if new != text:
    path.write_text(new, encoding="utf-8")
PY
