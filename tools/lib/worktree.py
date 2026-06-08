"""worktree — git worktree 기반 작업 격리. 에이전트마다 독립 작업트리/브랜치.

repo 가 git 이 아니면 명확히 보고하고 no-op. 모든 명령은 dry-run 지원.
"""
from __future__ import annotations
import os
import subprocess

__tool_version__ = "0.1.0"


def is_git_repo(repo):
    return subprocess.run(["git", "-C", repo, "rev-parse", "--is-inside-work-tree"],
                          capture_output=True).returncode == 0


def _run(cmd, dry):
    print("  $ " + " ".join(cmd))
    if dry:
        return 0
    return subprocess.call(cmd)


def create(repo, branch, wt_path, base="HEAD", dry=False):
    if not is_git_repo(repo):
        print("[worktree] git repo 아님: %s (no-op)" % repo)
        return None
    os.makedirs(os.path.dirname(os.path.abspath(wt_path)), exist_ok=True)
    _run(["git", "-C", repo, "worktree", "add", "-b", branch, os.path.abspath(wt_path), base], dry)
    return os.path.abspath(wt_path)


def remove(repo, wt_path, dry=False):
    if not is_git_repo(repo):
        return False
    _run(["git", "-C", repo, "worktree", "remove", "--force", os.path.abspath(wt_path)], dry)
    return True


def listing(repo):
    if not is_git_repo(repo):
        return []
    out = subprocess.run(["git", "-C", repo, "worktree", "list"], capture_output=True, text=True)
    return out.stdout.strip().splitlines()
