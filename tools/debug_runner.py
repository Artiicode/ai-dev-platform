#!/usr/bin/env python3
"""debug_runner — scenario/debug.md 플레이북을 구동 (빌드→ssh→scp→실행→로그→커밋).

안전 우선:
  - 기본 dry-run: 실제 실행 없이 모든 명령을 출력.
  - --execute: 노드 락 획득 + 위험 단계마다 승인 게이트(approval) 통과 필요.
  - 시크릿은 hw/<target>.md 의 *이름 참조*만 사용(ssh-agent/vault). 평문 금지.
  - 디버그 코드 보존(<ticket>-<name>-debug 브랜치) / 클린 커밋은 사람 승인.

hw 정보: projects/<node>/hw/<target>.md (host/user/port/deploy_path/ssh_key_ref).
"""
from __future__ import annotations
import argparse
import datetime
import os
import re
import subprocess
import sys

_LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")
sys.path.insert(0, _LIB)
import approval  # noqa
import locks     # noqa
import worktree  # noqa


def parse_hw(node_dir, target):
    for cand in ("%s.md" % target, "%s.example.md" % target):
        p = os.path.join(node_dir, "hw", cand)
        if os.path.exists(p):
            text = open(p, encoding="utf-8").read()
            info = {"_file": os.path.relpath(p, node_dir)}
            for line in text.splitlines():
                m = re.match(r"\s*([a-zA-Z_]+):\s*(.+?)\s*(#.*)?$", line)
                if m:
                    info.setdefault(m.group(1), m.group(2).strip())
            return info
    return None


def _append_worklog(node_dir, ticket, msg):
    p = os.path.join(node_dir, "history", "worklog", "%s.md" % ticket)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    ts = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    if not os.path.exists(p):
        open(p, "w", encoding="utf-8").write(
            "---\nticket: %s\nstatus: in-progress\n---\n# %s (debug 저널)\n\n## 진행 로그\n" % (ticket, ticket))
    with open(p, "a", encoding="utf-8") as f:
        f.write("- %s — %s\n" % (ts, msg))


def _sh(cmd, dry):
    print("    $ " + " ".join(cmd))
    if dry:
        return 0, "(dry-run)"
    r = subprocess.run(cmd, capture_output=True, text=True)
    out = (r.stdout or "") + (r.stderr or "")
    print(out.rstrip()[:2000])
    return r.returncode, out


def run(node_dir, ticket, name, target, build, run_cmd, execute):
    dry = not execute
    hw = parse_hw(node_dir, target)
    if not hw:
        print("[debug] hw 정보 없음: hw/%s(.example).md" % target, file=sys.stderr); return 1
    host, user = hw.get("host"), hw.get("user", "root")
    port, dpath = hw.get("port", "22"), hw.get("deploy_path", "/root")
    key_ref = hw.get("ssh_key_ref", "(ssh-agent)")
    remote = "%s@%s" % (user, host)

    print("=== 디버그 플레이북: %s-%s -> %s ===" % (ticket, name, target))
    print("타겟: %s:%s (port %s)  시크릿참조: %s  모드: %s" %
          (remote, dpath, port, key_ref, "EXECUTE" if execute else "DRY-RUN"))
    print("플랫폼 정책: platform/policies/approval-gates.md\n")

    owner = "debug-runner:%s" % ticket
    lock_ctx = locks.lock(node_dir, owner, ticket=ticket) if execute else _null()
    with lock_ctx:
        # 1) 시크릿 접근 게이트
        if execute and not approval.gate(node_dir, "시크릿 접근(ssh)", "ref=%s for %s" % (key_ref, remote)):
            return 2

        # 2) scp 전송
        if build:
            scp = ["scp", "-P", str(port), build, "%s:%s/" % (remote, dpath)]
            print("[2] 전송"); 
            if execute and not approval.gate(node_dir, "원격 전송(scp)", " ".join(scp)):
                return 2
            rc, _ = _sh(scp, dry)
            if rc != 0 and execute:
                print("[debug] scp 실패"); return rc
        else:
            print("[2] 전송 생략(--build 없음)")

        # 3) 원격 실행
        rc_cmd = run_cmd or ("%s/%s" % (dpath, os.path.basename(build)) if build else "echo no-run-cmd")
        ssh = ["ssh", "-p", str(port), remote, rc_cmd]
        print("[3] 실행")
        if execute and not approval.gate(node_dir, "원격 실행(ssh)", " ".join(ssh)):
            return 2
        rc, log = _sh(ssh, dry)

        # 4) 결과 + worklog
        status = "성공" if rc == 0 else "실패(rc=%s)" % rc
        print("[4] 결과: %s" % status)
        if execute:
            _append_worklog(node_dir, ticket, "debug 실행 %s @ %s (%s)" % (status, target, name))

        # 5) git: 디버그 브랜치 보존 + 클린 커밋 (승인)
        repo = os.path.join(node_dir, "repo")
        print("[5] git 분기 계획 (repo=%s)" % repo)
        debug_branch = "%s-%s-debug" % (ticket, name)
        clean_branch = "%s-%s" % (ticket, name)
        print("    디버그 보존 브랜치: %s" % debug_branch)
        print("    클린 커밋 브랜치  : %s (디버그 코드 제외 — 사람이 확정)" % clean_branch)
        if execute:
            if approval.gate(node_dir, "디버그 브랜치 보존(git)", "branch %s" % debug_branch):
                worktree.create(repo, debug_branch, os.path.join(node_dir, "state", "wt-%s" % debug_branch), dry=False)
            if approval.gate(node_dir, "클린 커밋(git)", "branch %s — 디버그 코드 제외 확인" % clean_branch):
                _append_worklog(node_dir, ticket, "클린 커밋 승인: %s" % clean_branch)
        else:
            print("    (dry-run: 승인 게이트는 --execute 시 적용)")
    print("\n[debug] 완료(%s)." % ("EXECUTE" if execute else "DRY-RUN"))
    return 0


import contextlib
@contextlib.contextmanager
def _null():
    yield


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--node", required=True)
    ap.add_argument("--ticket", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--target", default="jetson_agx_orin")
    ap.add_argument("--build", default=None, help="전송할 산출물 경로")
    ap.add_argument("--run-cmd", default=None, help="원격 실행 명령")
    ap.add_argument("--execute", action="store_true", help="실제 실행(기본은 dry-run)")
    a = ap.parse_args()
    sys.exit(run(a.node, a.ticket, a.name, a.target, a.build, a.run_cmd, a.execute))


if __name__ == "__main__":
    main()
