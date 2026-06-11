#!/usr/bin/env bash
# ensure_ready — idempotent first-run bootstrap guard.
# Safe and fast to call from ANY entry point (./harness launcher, Makefile, hooks).
# Instant no-op once `.harness-ready` exists and the venv is present; the heavy work
# (venv, deps, entry-rule symlinks, git hooks, vectors) runs only on the first call,
# delegated to post_clone.sh (which stamps `.harness-ready` on success).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

[ "${HARNESS_SKIP_READY:-}" = "1" ] && exit 0   # explicit bypass (CI/tests)

STAMP="$ROOT/.harness-ready"
if [ -f "$STAMP" ] && [ -x "$ROOT/.venv/bin/python" ]; then
  exit 0   # already prepared
fi

echo "[harness] first-run bootstrap (one time; set HARNESS_SKIP_READY=1 to skip)…" >&2
# Route progress to stderr so callers with a meaningful stdout stay clean.
bash "$ROOT/scripts/post_clone.sh" 1>&2
