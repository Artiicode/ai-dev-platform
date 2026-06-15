#!/usr/bin/env python3
"""node_git — per-node metadata git, auto/forcibly managed by agents.

A project node (`projects/<name>-node/`) keeps its OWN git history for the AI
operational data (context/scenario/history/info/manifest). The platform repo
git-ignores `/projects/*`, so this nested `.git` is invisible to it — no
submodule, no pollution of the platform log.

The project CODE lives in `repo/` and is an EXTERNAL object managed in its own
repository elsewhere; the node git NEVER tracks it (`/repo` is git-ignored here).
That separation is the hard invariant this module guarantees.
"""
from __future__ import annotations
import os
import subprocess

# Always excluded from node git. `/repo` is the hard invariant: the external
# project code (dir, clone, submodule, or symlink) must never be absorbed into
# the node's history.
_GITIGNORE_BASE = """\
# External project code — managed in its own repo elsewhere, NEVER by the node.
/repo

# Transient runtime (locks / ingest state)
state/lock.json
state/ingest.json

# Regenerable embeddings — rebuilt from archives/ (`harness rebuild`)
info/vector/*.bin
info/vector/*.faiss
info/vector/*.lance/
info/vector/store.db
info/vector/*.db-journal

# Secrets — never commit (reference by name only)
.env
*.key
*.pem
**/secrets/**

# Caches
__pycache__/
*.pyc
.DS_Store
"""

_MARKER = "# --- node-git baseline (auto-managed) ---"


def _git(node_dir, *args):
    return subprocess.run(["git", "-C", node_dir, *args], capture_output=True, text=True)


def has_git():
    try:
        subprocess.run(["git", "--version"], capture_output=True)
        return True
    except (OSError, FileNotFoundError):
        return False


def is_repo(node_dir):
    return os.path.isdir(os.path.join(node_dir, ".git"))


def ensure_gitignore(node_dir):
    """Ensure the node `.gitignore` exists and excludes the baseline (idempotent).
    Preserves any existing/private rules, appending only the missing baseline lines."""
    path = os.path.join(node_dir, ".gitignore")
    existing = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
    have = {ln.strip() for ln in existing.splitlines()}
    missing = [ln for ln in _GITIGNORE_BASE.splitlines()
               if ln.strip() and not ln.startswith("#") and ln.strip() not in have]
    if not existing:
        open(path, "w", encoding="utf-8").write(_GITIGNORE_BASE)
    elif missing:
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n%s\n%s\n" % (_MARKER, "\n".join(missing)))
    return path


def ensure_repo(node_dir):
    """Initialize the node's git repo if missing (+ .gitignore + initial commit).
    Idempotent and best-effort. Returns a short status string."""
    if not has_git():
        return "git-missing"
    ensure_gitignore(node_dir)
    if is_repo(node_dir):
        return "exists"
    r = _git(node_dir, "-c", "init.defaultBranch=main", "init")
    if r.returncode != 0:
        return "init-failed: %s" % r.stderr.strip()
    commit(node_dir, "chore(node): initialize node metadata git")
    return "initialized"


def commit(node_dir, message):
    """Stage all node changes (repo/ excluded via .gitignore) and commit if anything
    changed. Best-effort — never raises. Returns a short status string."""
    if not has_git():
        return "git-missing"
    if not is_repo(node_dir):
        st = ensure_repo(node_dir)        # auto-provision so callers needn't think about it
        if st == "initialized":
            return "initialized"          # initial commit already captured everything
        if st not in ("exists",):
            return st
    _git(node_dir, "add", "-A")
    if _git(node_dir, "diff", "--cached", "--quiet").returncode == 0:
        return "no-changes"
    r = _git(node_dir, "commit", "-m", message)
    return "committed" if r.returncode == 0 else "commit-failed: %s" % r.stderr.strip()


def status(node_dir):
    """Porcelain status of the node git (empty string if clean / not a repo)."""
    if not is_repo(node_dir):
        return ""
    return _git(node_dir, "status", "--porcelain").stdout.strip()


def repo_tracked(node_dir):
    """True if repo/ (external code) leaked into node git tracking — invariant violation."""
    if not is_repo(node_dir):
        return False
    return bool(_git(node_dir, "ls-files", "repo", "repo/").stdout.strip())


def main():
    import argparse
    ap = argparse.ArgumentParser(description="per-node metadata git")
    ap.add_argument("node", help="node dir (projects/<name>-node)")
    ap.add_argument("-m", "--message", default=None, help="commit message (default: ensure repo only)")
    a = ap.parse_args()
    if a.message:
        print("[node-git] %s" % commit(a.node, a.message))
    else:
        print("[node-git] %s" % ensure_repo(a.node))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
