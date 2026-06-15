#!/usr/bin/env python3
"""import_items — 외부 항목 목록(JSON/TSV)을 위키 페이지로 일괄 적재(소스 비종속).

Jira 티켓·GitHub PR 같은 외부 소스를 1급 위키 페이지로 둔다(Robert 의 jira/·starfish/ 패턴).
실제 fetch 는 소스별 도구(Jira MCP, `gh` CLI 등)가 JSON/TSV 로 떨궈주고, 이 importer 가 그것을
type=ticket/pr 위키 페이지(키/상태/url 프론트매터)로 변환·임베딩한다 — 플랫폼 코어는 소스에 비종속.

입력 항목 필드(유연): key|id, title|summary, body|description, status, url, type, updated.
JSON: [{...}, ...] 또는 {"items":[...]}.  TSV: 첫 줄 헤더.
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import sys

_LIB = os.path.join(os.path.dirname(__file__), "..", "lib")
sys.path.insert(0, _LIB)
import wiki        # noqa: E402
import provenance  # noqa: E402


def _load(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        obj = json.load(open(path, encoding="utf-8"))
        return obj.get("items", obj) if isinstance(obj, dict) else obj
    delim = "\t" if ext in (".tsv", ".tab") else ","
    return list(csv.DictReader(open(path, encoding="utf-8"), delimiter=delim))


def _field(it, *names, default=""):
    for n in names:
        if it.get(n):
            return str(it[n])
    return default


def _body(it):
    body = _field(it, "body", "description", "summary")
    head = []
    for label, val in (("key", _field(it, "key", "id")), ("status", _field(it, "status")),
                       ("url", _field(it, "url", "link")), ("updated", _field(it, "updated"))):
        if val:
            head.append("- %s: %s" % (label, val))
    return ("\n".join(head) + ("\n\n" if head else "") + body).strip() or "(내용 없음)"


def run(node_dir, path, type=None, dry_run=False):
    if not os.path.exists(path):
        print("[import] 파일 없음: %s" % path, file=sys.stderr); return 1
    items = _load(path)
    if not items:
        print("[import] 항목 없음"); return 0
    embedder = None
    n = 0
    for it in items:
        if not isinstance(it, dict):
            continue
        key = _field(it, "key", "id")
        title = _field(it, "title", "summary", default=key) or key or "untitled"
        itype = type or _field(it, "type", default="ticket")
        slug = wiki.slugify("%s %s" % (key, title)) if key else wiki.slugify(title)
        extra = {}
        for f in ("key", "id", "status", "url", "updated"):
            v = _field(it, f)
            if v:
                extra[f if f != "id" else "key"] = v
        print("[import] %-12s %s -> wiki:%s [type=%s]" % (key or "-", title[:40], slug, itype))
        if dry_run:
            continue
        res = wiki.upsert(node_dir, title=title, body=_body(it), slug=slug, type=itype,
                          sources=[{"id": key or title}], extra=extra)
        if embedder is None:
            from router import _load_embedder
            embedder = _load_embedder()
        wiki.embed_page(node_dir, res["slug"], embedder)
        provenance.record(node_dir, entry_id=key or slug, store="wiki", location=res["path"],
                          source=path, tool="import_items", route="wiki", route_by="import:%s" % itype)
        n += 1
    if not dry_run and n:
        wiki.reindex(node_dir)
    print("[import] %d 페이지 적재%s" % (n, " (dry-run)" if dry_run else ""))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--node", required=True)
    ap.add_argument("--file", required=True, help="JSON/TSV 항목 목록")
    ap.add_argument("--type", default=None, help="강제 type(예: ticket, pr). 미지정 시 항목별 type 또는 ticket")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    sys.exit(run(a.node, a.file, a.type, a.dry_run))


if __name__ == "__main__":
    main()
