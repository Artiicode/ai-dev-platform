#!/usr/bin/env python3
"""session — `harness start`: interactively pick/persist the default harness and claude launch
flags, then open a tmux workspace (window "dev"): left = claude (in the cloned platform dir by
default; --cwd overrides) / right-top = tmux cheatsheet then a free shell / right-bottom = usage.

Selection uses a small stdlib arrow-key picker (↑/↓, number keys, Enter) — no extra deps,
with a numbered-input fallback when stdin/stdout aren't a TTY. Machine-local choices live in
.harness-local.json (gitignored) — not secrets, just per-user prefs kept out of the template.
"""
from __future__ import annotations
import json
import os
import shlex
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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


def _yes(prompt, default="y"):
    return _ask(prompt, default).lower().startswith("y")


def _select_numbered(title, options, default):
    print("? %s" % title)
    for i, (lab, _) in enumerate(options):
        print("    [%d] %s%s" % (i + 1, lab, "   (기본)" if i == default else ""))
    ans = _ask("번호 선택 [%d]: " % (default + 1), str(default + 1))
    if ans.isdigit() and 1 <= int(ans) <= len(options):
        return options[int(ans) - 1][1]
    return options[default][1]


def _select(title, options, default=0):
    """Arrow-key single-select. options: list of (label, value). Returns the chosen value.

    ↑/↓ move, number keys jump, Enter confirms. Falls back to numbered input without a TTY."""
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return options[default][1]
    try:
        import termios
        import tty
    except Exception:
        return _select_numbered(title, options, default)

    idx = default
    n = len(options)
    sys.stdout.write("\033[1m? %s\033[0m  \033[2m(↑/↓ · 숫자 · Enter)\033[0m\n" % title)
    sys.stdout.write("\n" * n)   # reserve option lines

    def render():
        sys.stdout.write("\033[%dA" % n)   # cursor up to first option line
        for i, (lab, _) in enumerate(options):
            sel = i == idx
            pointer = "\033[36m❯\033[0m" if sel else " "
            text = "\033[1;36m%s\033[0m" % lab if sel else lab
            sys.stdout.write("\r\033[K %s \033[2m[%d]\033[0m %s\n" % (pointer, i + 1, text))
        sys.stdout.flush()

    render()
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        while True:
            ch = sys.stdin.read(1)
            if ch in ("\r", "\n"):
                break
            if ch == "\x03":
                raise KeyboardInterrupt
            if ch == "\x1b":                       # arrow escape seq
                if sys.stdin.read(1) == "[":
                    a = sys.stdin.read(1)
                    if a == "A":
                        idx = (idx - 1) % n
                        render()
                    elif a == "B":
                        idx = (idx + 1) % n
                        render()
            elif ch.isdigit() and 1 <= int(ch) <= n:
                idx = int(ch) - 1
                render()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return options[idx][1]


def _choose_harness(cfg, override):
    if override:
        return override
    if cfg.get("default_harness"):
        return cfg["default_harness"]
    h = _select("사용할 하네스 (진입규칙 주입 대상)?",
                [("claude-code", "claude-code"), ("cursor", "cursor")], 0)
    if _yes("'%s' 를 기본값으로 저장할까요? [Y/n]: " % h):
        cfg["default_harness"] = h
        _save_cfg(cfg)
    return h


def _choose_claude_cmd(cfg, override_skip):
    if override_skip is not None:
        skip = override_skip
    elif "claude_skip_perms" in cfg:
        skip = cfg["claude_skip_perms"]
    else:
        skip = _select("좌측 claude 실행 방식?",
                       [("기본 권한 — 확인 프롬프트 유지(안전)", False),
                        ("--dangerously-skip-permissions — 프롬프트 없음", True)], 0)
        if _yes("이 선택을 기본값으로 저장할까요? [Y/n]: "):
            cfg["claude_skip_perms"] = skip
            _save_cfg(cfg)
    return ["claude", "--dangerously-skip-permissions"] if skip else ["claude"]


def _cheatsheet_cmd():
    """A bash command that prints a clean, aligned tmux cheatsheet once, then leaves the pane
    as a usable shell. Fixed-width ASCII chords come first; Korean (double-width) descriptions
    trail with nothing after them, so alignment holds at any pane width. ANSI via bash $'...'."""
    C, R, B, D = "\\033[36m", "\\033[0m", "\\033[1m", "\\033[2m"   # cyan / reset / bold / dim
    rows = [
        ("C-b d", "      detach (분리)"),
        ("C-b \\xe2\\x86\\x90 \\xe2\\x86\\x92 \\xe2\\x86\\x91 \\xe2\\x86\\x93", "  pane 이동 (o 순환)"),
        ("C-b z", "      zoom 팬 확대/복원"),
        ('C-b "', "      가로 분할 (split-h)"),
        ("C-b %", "      세로 분할 (split-v)"),
        ("C-b x", "      pane 닫기"),
        ("C-b [", "      스크롤/복사 (q 종료)"),
        ("C-b c , Spc", "  새 창 / 이름변경 / 레이아웃"),
    ]
    title = "$'%s%s┌─ tmux cheatsheet%s%s ──────────────%s  prefix: %sCtrl-b%s'" % (B, C, R, D, R, B, R)
    args = [title]
    args += ["$'  %s%s%s%s'" % (C, chord, R, desc) for chord, desc in rows]
    args.append("$'  %sreattach%s   tmux attach -t <session>'" % (D, R))
    return "clear; printf '%s\\n' " + " ".join(args)


def _panes(session):
    out = subprocess.run(["tmux", "list-panes", "-t", session, "-F", "#{pane_id}"],
                         capture_output=True, text=True).stdout.split()
    return out


def start(session="harness", harness=None, skip_perms=None, cwd=None,
          use_tmux=True, attach=True):
    cfg = _load_cfg()
    h = _choose_harness(cfg, harness)
    # Wire the chosen harness's entry rules/skills (idempotent) via the CLI — no import coupling.
    subprocess.call([_py(), HARNESS_CLI, "use", h], cwd=ROOT)

    claude_cmd = _choose_claude_cmd(cfg, skip_perms)
    # Left pane runs where `harness` was invoked (the cloned platform dir in the normal case);
    # --cwd overrides.
    workdir = os.path.abspath(os.path.expanduser(cwd)) if cwd else os.getcwd()
    if not os.path.isdir(workdir):
        sys.stderr.write("[start] 작업 디렉토리 없음: %s\n" % workdir)
        return 2

    if not use_tmux:
        print("[start] tmux 없이 직접 실행(%s): %s" % (workdir, " ".join(claude_cmd)))
        return subprocess.call(claude_cmd, cwd=workdir)

    if not shutil.which("tmux"):
        sys.stderr.write("[start] tmux 미설치 — `sudo apt-get install tmux` 후 다시 시도(또는 --no-tmux).\n")
        return 2

    if subprocess.run(["tmux", "has-session", "-t", session], capture_output=True).returncode == 0:
        print("[start] 기존 tmux 세션 attach: %s" % session)
        return subprocess.call(["tmux", "attach", "-t", session]) if attach else 0

    usage_cmd = "%s %s tool ai-usage-monitor -- --watch 5" % (_py(), HARNESS_CLI)

    def tmux(*args):
        subprocess.run(["tmux", *args], check=True, cwd=ROOT)

    def send(pane, cmd):
        # tmux `-c workdir` only sets the START dir; an interactive shell's rc (.bashrc /
        # devtools-env.sh etc.) may cd elsewhere afterward. send-keys runs after the shell is
        # ready, so cd workdir HERE to pin each pane (esp. left=claude) to the invocation dir.
        full = "cd %s && %s" % (shlex.quote(workdir), cmd)
        subprocess.run(["tmux", "send-keys", "-t", pane, full, "Enter"], check=True)

    # Layout: left | right(top / bottom) — all panes start in workdir. Window name = "dev".
    tmux("new-session", "-d", "-s", session, "-n", "dev", "-c", workdir)
    p_left = _panes(session)[0]
    tmux("split-window", "-h", "-t", p_left, "-c", workdir)        # left | right
    p_right = [p for p in _panes(session) if p != p_left][0]
    tmux("split-window", "-v", "-t", p_right, "-c", workdir)       # right -> top / bottom
    p_rbot = [p for p in _panes(session) if p not in (p_left, p_right)][0]

    send(p_rbot, usage_cmd)            # 우하단: ai-usage-monitor --watch
    send(p_right, _cheatsheet_cmd())   # 우상단: tmux 치트시트 1회 출력 후 자유 셸
    send(p_left, " ".join(claude_cmd))  # 좌: claude (in workdir)

    # Window 2 "subtask": today's personal daily plan (오늘 할 일), auto-refreshing so /add-task shows.
    # Pass the command as ONE quoted string so `watch` doesn't try to parse `--show` as its own option.
    standup_view = 'watch -n 60 -t "%s %s standup --show"' % (_py(), HARNESS_CLI)
    tmux("new-window", "-t", session, "-n", "subtask", "-c", workdir)
    send("%s:subtask" % session, standup_view)

    tmux("select-window", "-t", "%s:dev" % session)
    tmux("select-pane", "-t", p_left)

    print("[start] tmux '%s': [dev] 좌=claude(%s)/우상=치트시트+셸/우하=usage  ·  [subtask] 오늘 플랜"
          % (session, workdir))
    if attach:
        return subprocess.call(["tmux", "attach", "-t", session])
    print("[start] attach: tmux attach -t %s" % session)
    return 0
