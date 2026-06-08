"""approval — 승인 게이트(HITL) + 감사 로그. platform/policies/approval-gates.md 구현 보조.

위험 행동(원격 실행, push, 삭제, 시크릿 접근 등)은 이 게이트를 통과해야 한다.
- HARNESS_AUTO_APPROVE=1 : 비대화(자동화/CI)에서 명시적 자동 승인.
- TTY 이면 대화형 y/N 프롬프트.
- 둘 다 아니면 거부(안전 우선).
모든 승인/거부는 state/audit.log 에 append.
"""
from __future__ import annotations
import datetime
import os
import sys

__tool_version__ = "0.1.0"


def audit(node_dir, action, detail, decision):
    p = os.path.join(node_dir, "state", "audit.log")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    ts = datetime.datetime.utcnow().isoformat() + "Z"
    with open(p, "a", encoding="utf-8") as f:
        f.write("%s\t%s\t%s\t%s\n" % (ts, decision, action, detail))


def gate(node_dir, action, detail, auto_env="HARNESS_AUTO_APPROVE"):
    """승인되면 True. 결과를 감사 로그에 기록."""
    if os.environ.get(auto_env) == "1":
        audit(node_dir, action, detail, "AUTO-APPROVED")
        print("[approval] AUTO-APPROVED: %s" % action, file=sys.stderr)
        return True
    if sys.stdin.isatty():
        try:
            ans = input("[승인 필요] %s\n  %s\n진행하시겠습니까? [y/N] " % (action, detail))
        except EOFError:
            ans = ""
        ok = ans.strip().lower() in ("y", "yes")
        audit(node_dir, action, detail, "APPROVED" if ok else "DENIED")
        return ok
    audit(node_dir, action, detail, "BLOCKED-NONINTERACTIVE")
    print("[approval] 차단: 비대화 환경. HARNESS_AUTO_APPROVE=1 로 명시 승인 필요 — %s" % action,
          file=sys.stderr)
    return False
