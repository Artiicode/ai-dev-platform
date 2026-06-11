#!/usr/bin/env python3
"""session — `harness start`: pick/persist the default harness + claude launch flags,
then open a tmux workspace (left: claude / right-top: git status watch / right-bottom:
ai-usage-monitor --watch).

Machine-local prefs live in .harness-local.json (gitignored) — not secrets, just per-user
choices, kept out of the tracked template.
"""
from __future__ import annotations
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL = os.path.join(ROOT, ".harness-local.json")
HARNESS_CLI = os.path.join(ROOT, "tools", "harness_cli.py")


def _py():
    p = os.path.join(ROOT, ".venv", "bin", "python")
    return p if os.path.exists(p) else "python3"


def _load_cfg():
    if os.path.exists(LOCAL):
        try:
            return json.load(open(LOCAL, encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_cfg(cfg):
    json.dump(cfg, open(LOCAL, "w", encoding="utf-8"), indent=2, ensure_ascii=False)


def _ask(prompt, default):
    if not sys.stdin.isatty():
        return default
    try:
        ans = input(prompt).strip()
    except EOFError:
        return default
    return ans or default


def _choose_harness(cfg, override):
    if override:
        return override
    if cfg.get("default_harness"):
        return cfg["default_harness"]
    ans = _ask("사용할 하네스? [claude-code/cursor] (기본 claude-code): ", "claude-code")
    h = "cursor" if ans.lower().startswith("cur") else "claude-code"
    if _ask("이 하네스를 기본값으로 저장할까요? [Y/n]: ", "y").lower().startswith("y"):
        cfg["default_harness"] = h
        _save_cfg(cfg)
    return h


def _choose_claude_cmd(cfg, override_skip):
    if override_skip is not None:
        skip = override_skip
    elif "claude_skip_perms" in cfg:
        skip = cfg["claude_skip_perms"]
    else:
        skip = _ask("claude 를 --dangerously-skip-permissions 로 실행할까요? [y/N]: ", "n").lower().startswith("y")
        if _ask("이 선택을 기본값으로 저장할까요? [Y/n]: ", "y").lower().startswith("y"):
            cfg["claude_skip_perms"] = skip
            _save_cfg(cfg)
    return ["claude", "--dangerously-skip-permissions"] if skip else ["claude"]


def _panes(session):
    out = subprocess.run(["tmux", "list-panes", "-t", session, "-F", "#{pane_id}"],
                         capture_output=True, text=True).stdout.split()
    return out


def start(session="harness", harness=None, skip_perms=None, repo=None,
          use_tmux=True, attach=True):
    cfg = _load_cfg()
    h = _choose_harness(cfg, harness)
    # Wire the chosen harness's entry rules/skills (idempotent) via the CLI — no import coupling.
    subprocess.call([_py(), HARNESS_CLI, "use", h], cwd=ROOT)

    claude_cmd = _choose_claude_cmd(cfg, skip_perms)
    repo = os.path.abspath(repo) if repo else ROOT

    if not use_tmux:
        print("[start] tmux 없이 직접 실행: %s" % " ".join(claude_cmd))
        return subprocess.call(claude_cmd)

    if not shutil.which("tmux"):
        sys.stderr.write("[start] tmux 미설치 — `sudo apt-get install tmux` 후 다시 시도(또는 --no-tmux).\n")
        return 2

    if subprocess.run(["tmux", "has-session", "-t", session], capture_output=True).returncode == 0:
        print("[start] 기존 tmux 세션 attach: %s" % session)
        return subprocess.call(["tmux", "attach", "-t", session]) if attach else 0

    usage_cmd = "%s %s tool ai-usage-monitor -- --watch 5" % (_py(), HARNESS_CLI)
    gitwatch = ("watch -n2 \"git -C '%s' status -s; echo '----'; git -C '%s' diff --stat\""
                % (repo, repo))
    claude = " ".join(claude_cmd)

    def tmux(*args):
        subprocess.run(["tmux", *args], check=True, cwd=ROOT)

    def send(pane, cmd):
        subprocess.run(["tmux", "send-keys", "-t", pane, cmd, "Enter"], check=True)

    # Layout: left | right(top / bottom)  — robust to tmux base-index via pane IDs.
    tmux("new-session", "-d", "-s", session, "-c", ROOT)
    p_left = _panes(session)[0]
    tmux("split-window", "-h", "-t", p_left, "-c", ROOT)        # left | right
    p_right = [p for p in _panes(session) if p != p_left][0]
    tmux("split-window", "-v", "-t", p_right, "-c", ROOT)       # right -> top / bottom
    p_rbot = [p for p in _panes(session) if p not in (p_left, p_right)][0]
    p_rtop = p_right

    send(p_rbot, usage_cmd)    # 우하단: ai-usage-monitor --watch
    send(p_rtop, gitwatch)     # 우상단: git status watch (에이전트 작업 파일변경)
    send(p_left, claude)       # 좌: claude
    tmux("select-pane", "-t", p_left)

    print("[start] tmux 세션 '%s' 구성: 좌=claude / 우상=git watch(%s) / 우하=usage" % (session, repo))
    if attach:
        return subprocess.call(["tmux", "attach", "-t", session])
    print("[start] attach: tmux attach -t %s" % session)
    return 0
