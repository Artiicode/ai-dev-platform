#!/usr/bin/env python3
"""loop — 자율 검증 루프(loop engineering).

플랫폼은 모델·하네스 비종속이다. **안쪽 agent loop 는 설정된 하네스 CLI(claude-code 등)가**
계속 담당하고, 이 모듈은 그 바깥을 감싸는 **검증 루프(verify/guard)** 만 소유한다:

    worktree 격리 → ( 에이전트 1패스(headless) → harness verify → 가드 ) 반복
      → 통과: 커밋 + worklog + ONBOARDING 갱신
      → 정체/상한: 에스컬레이션(중단하고 사람에게 보고, worktree 보존)

가드(무한루프 방지):
  * --max-iters     반복 상한
  * 무진전 감지     에이전트가 새 변경을 못 만든 패스가 연속 2회면 중단
  * --timeout       패스당 벽시계 한도(headless 호출이 매달리면 죽이고 다음으로)

결정론적 검증기(harness verify)만 신뢰한다 — 에이전트의 자기보고는 종료 근거로 쓰지 않는다.
"""
from __future__ import annotations
import datetime
import hashlib
import json
import os
import subprocess
import sys

import worktree                      # tools/lib (sys.path)
import verify                        # tools/node (sys.path)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _now():
    return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")


def _registry():
    import registry
    return registry.load()


def _default_harness(explicit=None):
    if explicit:
        return explicit
    local = os.path.join(ROOT, ".harness-local.json")
    if os.path.exists(local):
        try:
            h = (json.load(open(local, encoding="utf-8")) or {}).get("default_harness")
            if h:
                return h
        except Exception:
            pass
    enabled = _registry().get("enabled") or []
    return enabled[0] if enabled else "claude-code"


def _headless_cmd(harness):
    cfg = (_registry().get("harnesses") or {}).get(harness) or {}
    cmd = cfg.get("headless")
    if not cmd:
        raise SystemExit(
            "[loop] 하네스 '%s' 에 headless 호출 레시피가 없습니다 — platform/harnesses.yaml 의 "
            "'%s.headless' 에 비대화형 명령(예: [\"claude\",\"-p\",...])을 추가하세요." % (harness, harness))
    return list(cmd)


def _read_report(node_dir):
    rp = os.path.join(node_dir, "state", "verify-report.md")
    if not os.path.exists(rp):
        return ""
    return open(rp, encoding="utf-8").read().strip()


def _diff_hash(workdir):
    """현재 작업트리의 변경 지문(tracked diff + untracked 목록). 패스 전후로 같으면 '무진전'."""
    try:
        diff = subprocess.run(["git", "-C", workdir, "diff", "HEAD"],
                              capture_output=True, text=True).stdout
        unt = subprocess.run(["git", "-C", workdir, "ls-files", "--others", "--exclude-standard"],
                             capture_output=True, text=True).stdout
    except Exception:
        return None
    return hashlib.sha256((diff + "\n" + unt).encode("utf-8", "replace")).hexdigest()


def _build_prompt(spec, ticket, workdir, last_report, i, max_iters):
    parts = [
        "너는 격리된 git worktree(`%s`) 안에서 자율적으로 코딩하는 에이전트다." % workdir,
        "이 저장소 루트의 AGENTS.md/CLAUDE.md 규약과 conventions/ 를 따른다.",
        "티켓 %s 의 스펙을 구현하라. 커밋/푸시는 하지 마라(루프가 검증 후 커밋한다)." % ticket,
        "",
        "## 스펙",
        spec or "(스펙 미지정 — 직전 verify 실패를 해소하라)",
    ]
    if last_report:
        parts += [
            "",
            "## 직전 verify 결과 (이것을 통과시키는 게 목표 — [ ] 가 실패)",
            "```",
            last_report[-2000:],
            "```",
            "실패한 체크를 분석해 코드를 고쳐라. 추측 말고 실패 출력에 근거해 수정하라.",
        ]
    parts += ["", "(반복 %d/%d)" % (i, max_iters)]
    return "\n".join(parts)


def _run_agent(cmd, prompt, cwd, timeout):
    """headless 하네스를 1회 실행. 프롬프트는 stdin 으로 전달. (ok, tail) 반환."""
    print("[loop]   $ %s   (cwd=%s, stdin=prompt %dB, timeout=%ds)"
          % (" ".join(cmd), os.path.relpath(cwd, ROOT), len(prompt), timeout))
    try:
        r = subprocess.run(cmd, cwd=cwd, input=prompt, capture_output=True,
                           text=True, timeout=timeout)
        out = ((r.stdout or "") + (r.stderr or "")).strip()
        return r.returncode == 0, out.splitlines()[-4:]
    except subprocess.TimeoutExpired:
        print("[loop]   ⏱ 패스 타임아웃(%ds) — 죽이고 다음 패스로." % timeout, file=sys.stderr)
        return False, ["(timeout %ds)" % timeout]
    except FileNotFoundError:
        raise SystemExit("[loop] headless 실행 파일을 찾을 수 없음: %s — 하네스 CLI 설치/PATH 확인." % cmd[0])


def _worklog(node_dir, ticket, entry):
    """history/worklog/<ticket>.md 에 타임스탬프 경과 append (MCP append_worklog 와 동일 포맷)."""
    wl = os.path.join(node_dir, "history", "worklog")
    os.makedirs(wl, exist_ok=True)
    path = os.path.join(wl, "%s.md" % ticket)
    created = not os.path.exists(path)
    with open(path, "a", encoding="utf-8") as f:
        if created:
            f.write("---\nticket: %s\nstatus: in-progress\nupdated: %s\n---\n\n## 진행 로그 (append-only)\n"
                    % (ticket, _now()))
        f.write("\n- [%s] %s\n" % (_now(), entry))
    return path


def _refresh(node_dir):
    try:
        import gen_onboarding
        gen_onboarding.generate(node_dir)
    except Exception:
        pass
    try:
        import node_git
        node_git.commit(node_dir, "chore(node): harness loop progress")
    except Exception:
        pass


def _commit_code(workdir, ticket, dry):
    """성공한 작업을 worktree 브랜치(=repo 자체 git)에 로컬 커밋만 한다. 푸시는 사람 승인."""
    msg = "feat(%s): loop-verified change" % ticket
    if dry:
        print("  $ git -C %s add -A && git commit -m '%s'" % (workdir, msg))
        return
    subprocess.call(["git", "-C", workdir, "add", "-A"])
    subprocess.call(["git", "-C", workdir, "commit", "-m", msg, "--no-verify"])


def run(node_dir, ticket, spec=None, max_iters=5, timeout=1200, base="HEAD",
        harness=None, commit=True, dry=False):
    harness = _default_harness(harness)
    cmd = _headless_cmd(harness)
    repo = os.path.join(node_dir, "repo")
    branch = "%s-loop" % ticket
    wt = os.path.join(node_dir, "worktree", branch)

    workdir = worktree.ensure(repo, branch, wt, base=base, dry=dry)
    if workdir is None:
        # repo 가 git 이 아니면 격리 불가 → repo/ 에서 직접 (격리 없음) 진행
        print("[loop] ⚠️ repo 가 git 이 아니라 worktree 격리 불가 — repo/ 에서 직접 실행(격리 없음).",
              file=sys.stderr)
        workdir = repo
    print("[loop] node=%s ticket=%s harness=%s workdir=%s max-iters=%d"
          % (os.path.basename(node_dir), ticket, harness, os.path.relpath(workdir, ROOT), max_iters))

    if dry:
        print("[loop] (dry-run) 1패스 프롬프트 미리보기:\n%s"
              % _build_prompt(spec, ticket, workdir, _read_report(node_dir), 1, max_iters))
        return 0

    last_report = ""
    prev_hash = _diff_hash(workdir)
    no_progress = 0

    for i in range(1, max_iters + 1):
        print("\n[loop] ── 패스 %d/%d ──" % (i, max_iters))
        prompt = _build_prompt(spec, ticket, workdir, last_report, i, max_iters)
        ok, tail = _run_agent(cmd, prompt, cwd=workdir, timeout=timeout)
        if not ok:
            print("[loop]   에이전트 비정상 종료/타임아웃: %s" % " / ".join(tail))

        rc = verify.run(node_dir, repo_dir=workdir)
        last_report = _read_report(node_dir)

        if rc == 0:
            print("[loop] ✅ verify 통과 (패스 %d) — 커밋 + worklog." % i)
            if commit:
                _commit_code(workdir, ticket, dry)
            _worklog(node_dir, ticket,
                     "harness loop: %d패스 만에 verify 전체 통과 (harness=%s, worktree=%s). 푸시는 사람 승인 대기."
                     % (i, harness, os.path.relpath(workdir, node_dir)))
            _refresh(node_dir)
            return 0

        cur = _diff_hash(workdir)
        no_progress = no_progress + 1 if cur == prev_hash else 0
        prev_hash = cur
        if no_progress >= 2:
            print("[loop] ⛔ 무진전(연속 2패스 변경 없음) — 자동 중단·에스컬레이션.", file=sys.stderr)
            break

    # 통과 못 하고 종료 → 에스컬레이션
    reason = "무진전 정체" if no_progress >= 2 else "max-iters(%d) 도달" % max_iters
    _worklog(node_dir, ticket,
             "harness loop 에스컬레이션(%s): verify 미통과. worktree(%s) 보존 — 사람 개입 필요.\n  마지막 리포트 요약: %s"
             % (reason, os.path.relpath(workdir, node_dir),
                " | ".join(l for l in last_report.splitlines() if l.startswith("- [ ]")) or "(없음)"))
    _refresh(node_dir)
    print("\n[loop] ⚠️ 에스컬레이션 — %s. verify 미통과로 중단했습니다." % reason, file=sys.stderr)
    print("[loop] worktree 보존: %s" % os.path.relpath(workdir, ROOT), file=sys.stderr)
    print("[loop] 마지막 verify 리포트:\n%s" % (last_report or "(없음)"), file=sys.stderr)
    return 1
