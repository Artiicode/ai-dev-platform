#!/usr/bin/env python3
"""verify — 코딩 규약/테스트 시나리오 기반 검증 루프(Plan→...→Verify 의 Verify).

node/conventions/verify.yaml 의 checks 를 repo/ (또는 지정 cwd)에서 실행하고 pass/fail 집계.
required 체크가 하나라도 실패하면 비정상 종료. 리포트는 state/verify-report.md 에 기록.

verify.yaml 예:
  checks:
    - { name: lint,   cmd: "ruff check .",       required: true }
    - { name: types,  cmd: "mypy .",             required: false }
    - { name: unit,   cmd: "pytest -q",          required: true }
    - { name: scenario-smoke, cmd: "bash scenario/test/smoke.sh", cwd: node, required: true }
"""
from __future__ import annotations
import argparse
import datetime
import os
import subprocess
import sys


def _load_checks(node_dir):
    p = os.path.join(node_dir, "conventions", "verify.yaml")
    if not os.path.exists(p):
        return None
    try:
        import yaml
        return (yaml.safe_load(open(p)) or {}).get("checks", [])
    except Exception as e:
        print("[verify] verify.yaml 파싱 실패: %s" % e, file=sys.stderr); return []


def run(node_dir):
    checks = _load_checks(node_dir)
    if checks is None:
        print("[verify] conventions/verify.yaml 없음 — 검증 항목 미정의(스킵)"); return 0
    if not checks:
        print("[verify] 정의된 체크 없음"); return 0
    repo = os.path.join(node_dir, "repo")
    results = []
    for c in checks:
        name, cmd = c.get("name", "?"), c.get("cmd", "")
        required = bool(c.get("required", True))
        cwd = node_dir if c.get("cwd") == "node" else repo
        print("[verify] %-16s $ %s  (cwd=%s)" % (name, cmd, os.path.relpath(cwd, node_dir)))
        try:
            r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=600)
            ok = r.returncode == 0
            tail = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()[-3:]
        except Exception as e:
            ok, tail = False, [str(e)]
        results.append((name, ok, required, tail))
        print("           %s" % ("PASS" if ok else ("FAIL(required)" if required else "FAIL(optional)")))

    ts = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    lines = ["# verify report — %s" % ts, ""]
    for name, ok, req, tail in results:
        lines.append("- [%s] %s%s" % ("x" if ok else " ", name, "" if req else " (optional)"))
        for t in tail:
            lines.append("    %s" % t)
    rp = os.path.join(node_dir, "state", "verify-report.md")
    os.makedirs(os.path.dirname(rp), exist_ok=True)
    open(rp, "w", encoding="utf-8").write("\n".join(lines))

    # Fold the fresh test result into the curated brief (best-effort) so a later agent sees it.
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import gen_onboarding
        gen_onboarding.generate(node_dir)
    except Exception:
        pass

    failed_req = [n for n, ok, req, _ in results if req and not ok]
    passed = sum(1 for _, ok, _, _ in results if ok)
    print("[verify] %d/%d PASS · 리포트: %s" % (passed, len(results), os.path.relpath(rp, node_dir)))
    if failed_req:
        print("[verify] 필수 실패: %s" % ", ".join(failed_req), file=sys.stderr); return 1
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--node", required=True)
    a = ap.parse_args()
    sys.exit(run(a.node))


if __name__ == "__main__":
    main()
