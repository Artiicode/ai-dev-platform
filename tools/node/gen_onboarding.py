#!/usr/bin/env python3
"""gen_onboarding — history/worklog + adr + info-index + manifest 를 스캔해
history/ONBOARDING.md (신규 에이전트의 큐레이션 진입점)를 생성한다.

원시 로그가 아니라 '현재 상태 스냅샷': 활성 티켓 / 최근 결정 / 미해결 / 정보 자산.
결정적·멱등 — 언제든 재생성 가능.
"""
from __future__ import annotations
import datetime
import glob
import os
import re
import sys


def _frontmatter(path):
    """md 상단 --- ... --- 블록을 dict 로. yaml 있으면 사용, 없으면 단순 파서."""
    text = open(path, encoding="utf-8", errors="replace").read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    body = text[m.end():] if m else text
    fm = {}
    if m:
        block = m.group(1)
        try:
            import yaml
            fm = yaml.safe_load(block) or {}
        except Exception:
            for line in block.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    fm[k.strip()] = v.strip()
    return fm, body


def _git_log(repo_dir, n):
    """노드 repo 의 최근 커밋 한 줄 요약. repo 는 보통 (심링크된) 실제 프로젝트 git 작업트리이므로
    이슈/디버깅/기능 작업이 커밋 메시지로 자동 축적된 이력원이다. git 아니면 빈 리스트."""
    import subprocess
    if not os.path.isdir(repo_dir):
        return []
    try:
        r = subprocess.run(["git", "-C", repo_dir, "log", "--oneline", "--no-decorate", "-n", str(n)],
                           capture_output=True, text=True, timeout=10)
        return [ln for ln in r.stdout.strip().splitlines() if ln] if r.returncode == 0 else []
    except Exception:
        return []


def _section(body, header):
    """'## header' 아래 텍스트 추출(다음 ## 전까지)."""
    m = re.search(r"^##+\s*%s.*?$(.*?)(^##\s|\Z)" % re.escape(header), body,
                  re.DOTALL | re.MULTILINE)
    return (m.group(1).strip() if m else "")


def generate(node_dir):
    name = "(unknown)"
    man = os.path.join(node_dir, "manifest.yaml")
    if os.path.exists(man):
        for line in open(man, encoding="utf-8"):
            if re.match(r"\s*name:", line):
                name = line.split(":", 1)[1].split("#")[0].strip(); break

    # worklog 스캔
    tickets = []
    for p in sorted(glob.glob(os.path.join(node_dir, "history", "worklog", "*.md"))):
        if os.path.basename(p).startswith("_"):
            continue
        fm, body = _frontmatter(p)
        tickets.append({
            "ticket": fm.get("ticket", os.path.basename(p)[:-3]),
            "name": fm.get("name", ""),
            "status": (fm.get("status") or "unknown"),
            "updated": fm.get("updated", ""),
            "open_issues": _section(body, "미해결"),
        })
    active = [t for t in tickets if t["status"] in ("open", "in-progress", "blocked")]
    done = [t for t in tickets if t["status"] == "done"]

    # adr 스캔
    adrs = []
    for p in sorted(glob.glob(os.path.join(node_dir, "history", "adr", "*.md"))):
        first = open(p, encoding="utf-8").readline().lstrip("# ").strip()
        adrs.append((os.path.basename(p), first))

    # info 자산
    md_n = len([x for x in glob.glob(os.path.join(node_dir, "info", "md", "*")) if os.path.isfile(x)])
    db_n = len(glob.glob(os.path.join(node_dir, "info", "db", "*.sqlite")))
    has_vec = os.path.exists(os.path.join(node_dir, "info", "vector", "store.db"))

    ts = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    L = []
    L.append("---")
    L.append("title: 에이전트 온보딩 브리프")
    L.append("status: living")
    L.append("generated: true")
    L.append("generated_at: %s" % ts)
    L.append("---")
    L.append("# 온보딩 — %s 현재 상태 (신규 에이전트가 먼저 읽음)\n" % name)
    L.append("> 자동 생성(`harness onboard`). worklog/adr 로부터 갱신되는 큐레이션 진입점.\n")

    L.append("## 한눈에")
    L.append("- 프로젝트: **%s**" % name)
    L.append("- 활성 티켓: %d개 / 완료: %d개" % (len(active), len(done)))
    L.append("- 정보 자산: md %d · sql %d · vector %s\n" % (md_n, db_n, "있음" if has_vec else "없음"))

    L.append("## 활성 티켓")
    if active:
        for t in active:
            L.append("- **%s** %s — `%s` (updated %s)" %
                     (t["ticket"], t["name"], t["status"], t["updated"]))
    else:
        L.append("- (없음)")
    L.append("")

    L.append("## 최근 결정 (history/adr)")
    if adrs:
        for fn, title in adrs[-5:]:
            L.append("- %s — %s" % (fn, title))
    else:
        L.append("- (없음)")
    L.append("")

    L.append("## 알려진 이슈 / 미해결")
    issues = [(t["ticket"], t["open_issues"]) for t in active if t["open_issues"]]
    if issues:
        for tk, txt in issues:
            L.append("- **%s**: %s" % (tk, txt.replace("\n", " ")[:200]))
    else:
        L.append("- (없음)")
    L.append("")

    L.append("## 최근 코드 작업 (repo git)")
    gitlog = _git_log(os.path.join(node_dir, "repo"), 12)
    if gitlog:
        L.extend("- %s" % ln for ln in gitlog)
    else:
        L.append("- (repo 가 git 작업트리가 아니거나 커밋 없음)")
    L.append("")

    L.append("## 테스트/검증 최근 결과")
    vr = os.path.join(node_dir, "state", "verify-report.md")
    if os.path.exists(vr):
        rep = open(vr, encoding="utf-8").read().strip().splitlines()
        L.extend(rep[:14])
    else:
        L.append("- (verify 미실행 — `harness verify <node>`)")
    L.append("")

    L.append("## 오늘 스탠드업")
    try:
        import standup
        stxt = standup.show(standup.node_base(node_dir)).strip()
    except Exception:
        stxt = ""
    if stxt:
        idx = stxt.find("## [진행사항]")
        L.append(stxt[idx:] if idx >= 0 else stxt)
    else:
        L.append("- (오늘 기록 없음 — `harness standup <node> --add ...`)")
    L.append("")

    L.append("## 시작 절차")
    L.append("1. `platform/prompts/global-system.md` 규칙 숙지.")
    L.append("2. 활성 티켓의 `history/worklog/<티켓>.md` 확인.")
    L.append("3. 코딩은 `code/coding_convention/`, 디버그는 `scenario/debug.md`.")
    L.append("4. 사실/데이터는 MCP `search_info`/`query_sql` 또는 `info/`.\n")

    out = os.path.join(node_dir, "history", "ONBOARDING.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write("\n".join(L))
    return out, len(active), len(adrs)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--node", required=True)
    a = ap.parse_args()
    out, na, nadr = generate(a.node)
    print("[onboard] 생성: %s (활성 티켓 %d, ADR %d)" % (out, na, nadr))


if __name__ == "__main__":
    main()
