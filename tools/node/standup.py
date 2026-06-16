#!/usr/bin/env python3
"""standup — daily standup / task log (<base>/<YYYY-MM-DD>.md).

Two bases share the same format and tooling:
  - node base:     <node>/history/standup        (project work standup; feeds ONBOARDING)
  - platform base: <ROOT>/standup                 (personal daily plan; shown in `harness start`)

Format (lists everywhere):
    ## [오늘 할 일]
    - [ ] 오후 2시 Qt 세미나        # /add-task 로 추가, 완료 시 - [x]
    ## [진행사항]
    - [HH:MM] 무엇을 진행 중인지
    ## [요약]
    - 오늘: ...
    - 내일: ...

When today's file doesn't exist it is created, seeding [오늘 할 일] from the most recent
previous day: its undone tasks (`- [ ]`) plus its [요약] '내일' line. Empty → "- 없음".
"""
from __future__ import annotations
import argparse
import datetime
import glob
import os
import re
import sys

TASKS = "## [오늘 할 일]"
PROGRESS = "## [진행사항]"
SUMMARY = "## [요약]"
_NONE = "- 없음"
_PH_PROGRESS = "- (작업하며 추가됨)"


def _today():
    return datetime.date.today().isoformat()


def _now_hm():
    return datetime.datetime.now().strftime("%H:%M")


def node_base(node_dir):
    return os.path.join(node_dir, "history", "standup")


def platform_base(root):
    return os.path.join(root, "standup")


def _node_name(node_dir):
    man = os.path.join(node_dir, "manifest.yaml")
    if os.path.exists(man):
        for line in open(man, encoding="utf-8"):
            m = re.match(r"\s*name:\s*(.+)", line)
            if m:
                return m.group(1).split("#")[0].strip()
    return os.path.basename(node_dir.rstrip("/")).removesuffix("-node")


def path(base, date=None):
    return os.path.join(base, "%s.md" % (date or _today()))


def list_days(base):
    days = [os.path.basename(x)[:-3] for x in glob.glob(os.path.join(base, "*.md"))]
    return sorted(x for x in days if re.match(r"\d{4}-\d{2}-\d{2}$", x))


def _section(lines, header):
    """(header_index, end_index) for a '## ...' section; end = next '## ' or EOF. (-1,-1) if absent."""
    try:
        h = next(i for i, l in enumerate(lines) if l.strip() == header)
    except StopIteration:
        return -1, -1
    e = h + 1
    while e < len(lines) and not lines[e].strip().startswith("## "):
        e += 1
    return h, e


def _carry_over(base, today):
    """Seed task list from the most recent previous day: undone tasks + '내일' plan."""
    prev = [d for d in list_days(base) if d < today]
    if not prev:
        return []
    lines = open(path(base, prev[-1]), encoding="utf-8").read().splitlines()
    out = []
    h, e = _section(lines, TASKS)
    if h >= 0:
        for l in lines[h + 1:e]:
            m = re.match(r"\s*-\s*\[ \]\s*(.+)", l)   # unchecked only
            if m:
                out.append(m.group(1).strip())
    for l in lines:
        m = re.match(r"\s*-\s*내일:\s*(.+)", l)
        if m and m.group(1).strip():
            out.append(m.group(1).strip())
    # dedup preserving order
    seen, dedup = set(), []
    for t in out:
        if t not in seen:
            seen.add(t)
            dedup.append(t)
    return dedup


def _template(name, date, tasks):
    task_lines = "\n".join("- [ ] %s" % t for t in tasks) if tasks else _NONE
    return ("---\ntitle: 데일리 스탠드업\ndate: %s\n---\n# 스탠드업 — %s — %s\n\n"
            "%s\n%s\n\n%s\n%s\n\n%s\n- 오늘: \n- 내일: \n"
            % (date, name, date, TASKS, task_lines, PROGRESS, _PH_PROGRESS, SUMMARY))


def _ensure(base, name="daily", date=None):
    date = date or _today()
    p = path(base, date)
    os.makedirs(base, exist_ok=True)
    if not os.path.exists(p):
        open(p, "w", encoding="utf-8").write(_template(name, date, _carry_over(base, date)))
    return p


def _append_to_section(base, header, line, drop, name, date):
    p = _ensure(base, name, date)
    lines = open(p, encoding="utf-8").read().splitlines()
    h, e = _section(lines, header)
    if h < 0:
        lines += ["", header]
        h, e = len(lines) - 1, len(lines)
    body = [l for l in lines[h + 1:e] if l.strip() and l.strip() not in drop]
    body.append(line)
    new = lines[:h + 1] + [""] + body + [""] + lines[e:]
    open(p, "w", encoding="utf-8").write("\n".join(new).rstrip() + "\n")
    return p


def add_task(base, text, name="daily", date=None):
    return _append_to_section(base, TASKS, "- [ ] %s" % text, {_NONE}, name, date)


def add(base, item, name="daily", date=None):
    return _append_to_section(base, PROGRESS, "- [%s] %s" % (_now_hm(), item), {_PH_PROGRESS}, name, date)


def set_summary(base, today=None, tomorrow=None, name="daily", date=None):
    p = _ensure(base, name, date)
    lines = open(p, encoding="utf-8").read().splitlines()
    ft = fm = False
    for k, l in enumerate(lines):
        s = l.strip()
        if today is not None and s.startswith("- 오늘:"):
            lines[k] = "- 오늘: %s" % today
            ft = True
        if tomorrow is not None and s.startswith("- 내일:"):
            lines[k] = "- 내일: %s" % tomorrow
            fm = True
    extra = []
    if today is not None and not ft:
        extra.append("- 오늘: %s" % today)
    if tomorrow is not None and not fm:
        extra.append("- 내일: %s" % tomorrow)
    if extra:
        h, e = _section(lines, SUMMARY)
        lines = (lines + ["", SUMMARY] + extra) if h < 0 else (lines[:e] + extra + lines[e:])
    open(p, "w", encoding="utf-8").write("\n".join(lines).rstrip() + "\n")
    return p


def _progress_lines(p):
    """[진행사항] section non-placeholder bullets of a standup file."""
    if not os.path.exists(p):
        return []
    lines = open(p, encoding="utf-8").read().splitlines()
    h, e = _section(lines, PROGRESS)
    if h < 0:
        return []
    return [l.strip() for l in lines[h + 1:e]
            if l.strip().startswith("- ") and l.strip() not in (_PH_PROGRESS, _NONE)]


# Platform / data-pipeline operations — NOT project code work, so excluded from the daily
# plan roll-up (the user wants only compact code-level "what was done"). Heuristic, adjustable.
_ROLLUP_SKIP = (
    "인제스트", "ingest", "데이터 적재", "info/db", "info/wiki", "info/vector", "data/update",
    "provenance", "출처 기록", "재색인", "reindex", "rebuild", "재빌드",
    "온보딩 재생성", "onboarding", "index.yaml", "위키 인덱스",
)


def _is_meta(text):
    t = text.lower()
    return any(k.lower() in t for k in _ROLLUP_SKIP)


def _parse_hm(line):
    """'- [HH:MM] text' → ('HH:MM', text); else ('', stripped bullet text)."""
    m = re.match(r"\s*-\s*\[(\d{2}:\d{2})\]\s*(.+)", line)
    if m:
        return m.group(1), m.group(2).strip()
    return "", re.sub(r"^\s*-\s*", "", line).strip()


def project_rollup(root, date=None, per_node=6, width=88):
    """Aggregate TODAY's project CODE work across nodes into a compact, readable section for the
    personal daily plan. Reads each node's worklog (`- [<iso>] ...`) + standup [진행사항], drops
    platform/data-pipeline meta (ingestion 등), trims, caps per node. Read-only — agents just log
    via append_worklog / node standup; the plan rolls it up (no need to write the platform plan)."""
    date = date or _today()
    proj = os.path.join(root, "projects")
    if not os.path.isdir(proj):
        return ""
    groups = []
    for nd in sorted(glob.glob(os.path.join(proj, "*-node"))):
        if os.path.basename(nd) == "_template-node":
            continue
        items = []                                                    # (hhmm, text)
        for line in _progress_lines(path(node_base(nd), date)):       # node standup [진행사항]
            hm, text = _parse_hm(line)
            if text and not _is_meta(text):
                items.append((hm, text))
        wl = os.path.join(nd, "history", "worklog")
        for f in sorted(glob.glob(os.path.join(wl, "*.md"))):         # today's worklog entries
            ticket = os.path.basename(f)[:-3]
            for l in open(f, encoding="utf-8"):
                m = re.match(r"\s*-\s*\[(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2})[^\]]*\]\s*(.+)", l)
                if m and m.group(1) == date and not _is_meta(m.group(3)):
                    items.append((m.group(2), "(%s) %s" % (ticket, m.group(3).strip())))
        seen, uniq = set(), []                                        # dedup, keep latest per node
        for hm, text in items:
            if text not in seen:
                seen.add(text); uniq.append((hm, text))
        if not uniq:
            continue
        uniq.sort(key=lambda x: x[0])
        shown, more = uniq[-per_node:], len(uniq) - per_node
        lines = ["[%s]" % _node_name(nd)]
        for hm, text in shown:
            text = text if len(text) <= width else text[:width - 1] + "…"
            lines.append("    - %s%s" % ((hm + "  ") if hm else "", text))
        if more > 0:
            lines.append("    … 외 %d건" % more)
        groups.append("\n".join(lines))
    if not groups:
        return ""
    return "\n## 오늘 프로젝트 작업 (자동 집계 · %s)\n\n%s\n" % (date, "\n\n".join(groups))


def show(base, date=None, ensure=False, name="daily"):
    if ensure:
        _ensure(base, name, date)
    p = path(base, date)
    return open(p, encoding="utf-8").read() if os.path.exists(p) else ""


def main():
    ap = argparse.ArgumentParser(description="daily standup / task log")
    ap.add_argument("--base", required=True, help="standup 폴더 경로")
    ap.add_argument("--name", default="daily")
    ap.add_argument("--add-task", default=None)
    ap.add_argument("--add", default=None)
    ap.add_argument("--today", default=None)
    ap.add_argument("--tomorrow", default=None)
    ap.add_argument("--date", default=None)
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list:
        print("\n".join(list_days(a.base)) or "(없음)")
        return 0
    did = False
    if a.add_task:
        add_task(a.base, a.add_task, a.name, a.date); did = True
    if a.add:
        add(a.base, a.add, a.name, a.date); did = True
    if a.today is not None or a.tomorrow is not None:
        set_summary(a.base, a.today, a.tomorrow, a.name, a.date); did = True
    if a.show or not did:
        sys.stdout.write(show(a.base, a.date, ensure=True, name=a.name) or "(없음)\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
