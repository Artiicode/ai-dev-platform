#!/usr/bin/env python3
"""standup — per-node daily standup log (history/standup/<YYYY-MM-DD>.md).

Day-keyed scrum tracking: what's in progress today, and what's planned next, so a new
day's standup can be summarized at a glance. The agent updates it as work proceeds
(incrementally, in a batch, or on request). Format:

    ## [진행사항]
    - [HH:MM] <무엇을 진행 중인지>
    ## [요약]
    - 오늘: <오늘 진행 중인 것>
    - 내일: <내일 할 예정>
"""
from __future__ import annotations
import argparse
import datetime
import glob
import os
import re
import sys

PROGRESS = "## [진행사항]"
SUMMARY = "## [요약]"
_PLACEHOLDER = "- (작업하며 추가됨)"


def _today():
    return datetime.date.today().isoformat()


def _now_hm():
    return datetime.datetime.now().strftime("%H:%M")


def _node_name(node_dir):
    man = os.path.join(node_dir, "manifest.yaml")
    if os.path.exists(man):
        for line in open(man, encoding="utf-8"):
            m = re.match(r"\s*name:\s*(.+)", line)
            if m:
                return m.group(1).split("#")[0].strip()
    return os.path.basename(node_dir.rstrip("/")).removesuffix("-node")


def path(node_dir, date=None):
    return os.path.join(node_dir, "history", "standup", "%s.md" % (date or _today()))


def _template(node_name, date):
    return ("---\ntitle: 데일리 스탠드업\ndate: %s\n---\n# 스탠드업 — %s — %s\n\n"
            "%s\n%s\n\n%s\n- 오늘: \n- 내일: \n" % (date, node_name, date, PROGRESS, _PLACEHOLDER, SUMMARY))


def _ensure(node_dir, date):
    p = path(node_dir, date)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    if not os.path.exists(p):
        open(p, "w", encoding="utf-8").write(_template(_node_name(node_dir), date))
    return p


def _section_bounds(lines, header):
    """(header_index, end_index) for a '## ...' section; end is next '## ' or EOF. (-1,-1) if absent."""
    try:
        h = next(i for i, l in enumerate(lines) if l.strip() == header)
    except StopIteration:
        return -1, -1
    e = h + 1
    while e < len(lines) and not lines[e].strip().startswith("## "):
        e += 1
    return h, e


def add(node_dir, item, date=None):
    date = date or _today()
    p = _ensure(node_dir, date)
    lines = open(p, encoding="utf-8").read().splitlines()
    h, e = _section_bounds(lines, PROGRESS)
    if h < 0:
        lines += ["", PROGRESS]
        h, e = len(lines) - 1, len(lines)
    body = [l for l in lines[h + 1:e] if l.strip() and l.strip() != _PLACEHOLDER]
    body.append("- [%s] %s" % (_now_hm(), item))
    new = lines[:h + 1] + [""] + body + [""] + lines[e:]
    open(p, "w", encoding="utf-8").write("\n".join(new).rstrip() + "\n")
    return p


def set_summary(node_dir, today=None, tomorrow=None, date=None):
    date = date or _today()
    p = _ensure(node_dir, date)
    lines = open(p, encoding="utf-8").read().splitlines()
    found_today = found_tomorrow = False
    for k, l in enumerate(lines):
        s = l.strip()
        if today is not None and s.startswith("- 오늘:"):
            lines[k] = "- 오늘: %s" % today
            found_today = True
        if tomorrow is not None and s.startswith("- 내일:"):
            lines[k] = "- 내일: %s" % tomorrow
            found_tomorrow = True
    extra = []
    if today is not None and not found_today:
        extra.append("- 오늘: %s" % today)
    if tomorrow is not None and not found_tomorrow:
        extra.append("- 내일: %s" % tomorrow)
    if extra:
        h, e = _section_bounds(lines, SUMMARY)
        if h < 0:
            lines += ["", SUMMARY] + extra
        else:
            lines = lines[:e] + extra + lines[e:]
    open(p, "w", encoding="utf-8").write("\n".join(lines).rstrip() + "\n")
    return p


def show(node_dir, date=None):
    p = path(node_dir, date)
    return open(p, encoding="utf-8").read() if os.path.exists(p) else ""


def list_days(node_dir):
    d = os.path.join(node_dir, "history", "standup")
    days = [os.path.basename(x)[:-3] for x in glob.glob(os.path.join(d, "*.md"))]
    return sorted(x for x in days if re.match(r"\d{4}-\d{2}-\d{2}$", x))


def main():
    ap = argparse.ArgumentParser(description="per-node daily standup log")
    ap.add_argument("--node", required=True, help="노드 디렉토리 경로")
    ap.add_argument("--add", default=None, help="[진행사항] 에 항목 추가")
    ap.add_argument("--today", default=None, help="[요약] 오늘 진행 중")
    ap.add_argument("--tomorrow", default=None, help="[요약] 내일 예정")
    ap.add_argument("--date", default=None, help="대상 날짜(기본 오늘, YYYY-MM-DD)")
    ap.add_argument("--show", action="store_true", help="해당 날짜 스탠드업 출력")
    ap.add_argument("--list", action="store_true", help="기록된 날짜 목록")
    a = ap.parse_args()
    nd = a.node
    if a.list:
        print("\n".join(list_days(nd)) or "(없음)")
        return 0
    if a.add:
        print("[standup] 추가:", add(nd, a.add, a.date))
    if a.today is not None or a.tomorrow is not None:
        print("[standup] 요약 갱신:", set_summary(nd, a.today, a.tomorrow, a.date))
    if a.show or not (a.add or a.today is not None or a.tomorrow is not None):
        sys.stdout.write(show(nd, a.date) or "(스탠드업 없음 — --add 로 시작)\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
