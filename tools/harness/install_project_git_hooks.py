#!/usr/bin/env python3
"""Install AI-trailer strip/reject hooks into an arbitrary git repo (e.g. starfish).

Unlike install_hooks.py (platform Conventional Commits), this installs
commit-msg-no-ai-trailer as commit-msg so SW-NNN subjects remain valid.

Respects an existing core.hooksPath (e.g. a repo-committed hook directory
like starfish's tools/git-hooks/, wired up by the project's own
install-hooks.sh). Writing straight into <git-common-dir>/hooks in that case
would be silently inert -- git only reads hooks from core.hooksPath once it
is set. Instead this installs into a local-only directory
(<git-common-dir>/ai-dev-platform-hooks), chains any hook types the project
already provides (e.g. pre-commit) via a wrapper that execs the original by
absolute path, and repoints core.hooksPath (a local git config value, never
committed) at the combined directory. Nothing under the repo's own tracked
tree is touched.
"""
from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "tools", "hooks")

AI_TRAILER_HOOKS = {
    "strip-ai-trailers.sh": "strip-ai-trailers.sh",
    "prepare-commit-msg": "prepare-commit-msg",
    "commit-msg-no-ai-trailer": "commit-msg",
    "post-commit": "post-commit",
}

WRAPPER_TEMPLATE = """#!/usr/bin/env bash
# Installed by ai-dev-platform install_project_git_hooks.py.
# Chains the project's own {hook_name} hook. core.hooksPath was already an
# absolute, non-worktree-relative path when we found it ({original}), so we
# preserve that exact behavior rather than guessing a per-worktree location.
set -euo pipefail
original="{original}"
if [ -x "$original" ]; then
  exec "$original" "$@"
fi
exit 0
"""


def git_common_dir(repo: str) -> str:
    out = subprocess.check_output(
        ["git", "-C", repo, "rev-parse", "--git-common-dir"],
        text=True,
    ).strip()
    if not os.path.isabs(out):
        out = os.path.normpath(os.path.join(repo, out))
    return out


def existing_hooks_path(repo: str, common: str) -> tuple[str, bool]:
    """Return (absolute effective hooks dir, was_explicitly_configured)."""
    out = subprocess.run(
        ["git", "-C", repo, "config", "--get", "core.hooksPath"],
        text=True,
        capture_output=True,
        check=False,
    )
    configured = out.stdout.strip()
    if not configured:
        return os.path.join(common, "hooks"), False
    if not os.path.isabs(configured):
        configured = os.path.normpath(os.path.join(repo, configured))
    return configured, True


def install_ai_trailer_hooks(dst_dir: str) -> None:
    for src_name, dst_name in AI_TRAILER_HOOKS.items():
        src = os.path.join(SRC, src_name)
        dst = os.path.join(dst_dir, dst_name)
        if not os.path.isfile(src):
            print(f"[install-project-hooks] missing source: {src}", file=sys.stderr)
            raise SystemExit(1)
        shutil.copyfile(src, dst)
        os.chmod(dst, 0o755)
        print(f"[install-project-hooks] {dst}")


def chain_existing_hooks(project_hooks_dir: str, dst_dir: str) -> None:
    """For every hook type already present at project_hooks_dir that we are
    not overriding, install a wrapper in dst_dir that execs the original by
    absolute path."""
    if not os.path.isdir(project_hooks_dir):
        return
    for name in sorted(os.listdir(project_hooks_dir)):
        if name.endswith(".sample") or name in AI_TRAILER_HOOKS.values():
            continue
        src = os.path.join(project_hooks_dir, name)
        if not os.path.isfile(src) or not os.access(src, os.X_OK):
            continue
        wrapper = WRAPPER_TEMPLATE.format(hook_name=name, original=src)
        dst = os.path.join(dst_dir, name)
        with open(dst, "w", encoding="utf-8") as fh:
            fh.write(wrapper)
        st = os.stat(dst)
        os.chmod(dst, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        print(f"[install-project-hooks] {dst}  (chains {src})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("repo", help="Path to target git worktree or repo")
    args = ap.parse_args()
    repo = os.path.abspath(args.repo)
    if not os.path.isdir(repo):
        print(f"[install-project-hooks] not a directory: {repo}", file=sys.stderr)
        return 1
    try:
        common = git_common_dir(repo)
    except subprocess.CalledProcessError:
        print(f"[install-project-hooks] not a git repo: {repo}", file=sys.stderr)
        return 1

    effective, was_configured = existing_hooks_path(repo, common)

    # Idempotency: a prior run of this script may have already repointed
    # core.hooksPath at our own combined dir. Recover the true original from
    # the marker file we leave behind, instead of re-chaining from ourselves
    # (which would just wrap our own wrapper one layer deeper every run).
    marker = os.path.join(common, "ai-dev-platform-hooks", ".origin-hooks-path")
    if was_configured and os.path.normpath(effective) == os.path.normpath(
        os.path.join(common, "ai-dev-platform-hooks")
    ) and os.path.isfile(marker):
        with open(marker, encoding="utf-8") as fh:
            effective = fh.read().strip()

    if not was_configured:
        dst_dir = effective
        os.makedirs(dst_dir, exist_ok=True)
        install_ai_trailer_hooks(dst_dir)
        print(f"[install-project-hooks] done -> {dst_dir}")
        return 0

    if os.path.normpath(effective) == os.path.normpath(os.path.join(common, "hooks")):
        # core.hooksPath happens to be explicitly set but points at the
        # default location anyway; safe to install there directly.
        dst_dir = effective
        os.makedirs(dst_dir, exist_ok=True)
        install_ai_trailer_hooks(dst_dir)
        print(f"[install-project-hooks] done -> {dst_dir}")
        return 0

    # core.hooksPath already points somewhere else (a repo-committed hooks
    # dir, e.g. starfish's tools/git-hooks/). Writing into <common>/hooks
    # would be silently inert. Build a local-only combined directory that
    # chains the project's existing hooks and repoint core.hooksPath at it.
    print(
        f"[install-project-hooks] core.hooksPath already set to {effective} "
        f"(project-managed) -- installing a local-only combined dir instead "
        f"of the dead default location",
        file=sys.stderr,
    )
    dst_dir = os.path.join(common, "ai-dev-platform-hooks")
    os.makedirs(dst_dir, exist_ok=True)
    chain_existing_hooks(effective, dst_dir)
    install_ai_trailer_hooks(dst_dir)
    with open(os.path.join(dst_dir, ".origin-hooks-path"), "w", encoding="utf-8") as fh:
        fh.write(effective + "\n")
    subprocess.check_call(["git", "-C", repo, "config", "core.hooksPath", dst_dir])
    print(f"[install-project-hooks] core.hooksPath -> {dst_dir} (was {effective}, now chained)")
    print(f"[install-project-hooks] done -> {dst_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
