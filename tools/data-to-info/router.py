#!/usr/bin/env python3
"""data-to-info router — data/update/* 를 의미적 route(sql|rag|wiki) 로 실제 적재 (라우팅 v2).

route 결정(tools/data-to-info/routing.py): 힌트(파일명/프론트매터) → LLM 분류기(키 있을 때) → 크기 폴백.
route → 물리 store 매핑 (Phase 1):
  - sql  -> info/db/<name>.sqlite          (정형: 숫자·표)
  - rag  -> info/vector/store.db           (비정형·장문, sqlite-vec 임베딩)
  - wiki -> info/md/<name>[.md]            (작은 권위 문서; Phase 2 에서 엔티티 위키로 격상 예정)
추출 불가(라이브러리 부재 등) -> skip + 사유(원본 inbox 유지).

동작: 적재 → provenance 기록(route/route_by 포함) → 원본 archives/ 이동(멱등: 동일 sha skip).
임베딩: platform/models/models.yaml (기본 bge-m3, 폴백 hash). 추출: tools/lib/extractor.py
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import shutil
import sqlite3
import sys

_LIB = os.path.join(os.path.dirname(__file__), "..", "lib")
sys.path.insert(0, _LIB)
import provenance  # noqa: E402
import extractor   # noqa: E402
import routing     # noqa: E402  (sql|rag|wiki 결정: 힌트 → LLM 분류기 → 크기 폴백)

__tool_version__ = "0.3.0"
STRUCTURED = routing.STRUCTURED


def _rows_from_json(obj):
    if isinstance(obj, list):
        return [r for r in obj if isinstance(r, dict)]
    if isinstance(obj, dict):
        for v in obj.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
        return [obj]
    return []


def _ingest_sql(src, node_dir):
    name = os.path.splitext(os.path.basename(src))[0]
    table = "".join(c if c.isalnum() else "_" for c in name)
    db_path = os.path.join(node_dir, "info", "db", name + ".sqlite")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    ext = os.path.splitext(src)[1].lower()
    if ext == ".json":
        rows = _rows_from_json(json.load(open(src, encoding="utf-8")))
    else:
        delim = "\t" if ext == ".tsv" else ","
        rows = list(csv.DictReader(open(src, encoding="utf-8"), delimiter=delim))
    if not rows:
        return "info/db/%s.sqlite (empty)" % name
    cols = list({k for r in rows for k in r.keys()})
    col_defs = ", ".join('"%s"' % c for c in cols)
    placeholders = ", ".join("?" for _ in cols)
    db = sqlite3.connect(db_path)
    db.execute('DROP TABLE IF EXISTS "%s"' % table)
    db.execute('CREATE TABLE "%s" (%s)' % (table, col_defs))
    vals = [[json.dumps(r.get(c)) if isinstance(r.get(c), (dict, list)) else r.get(c)
             for c in cols] for r in rows]
    db.executemany('INSERT INTO "%s" (%s) VALUES (%s)' % (table, col_defs, placeholders), vals)
    db.commit(); db.close()
    return "info/db/%s.sqlite::%s (%d rows)" % (name, table, len(rows))


def _write_md(node_dir, name, text=None, src=None):
    """plain 원본은 그대로 복사, 추출 텍스트는 <name>.md 로 기록."""
    if src is not None:                       # plain copy
        dst = os.path.join(node_dir, "info", "md", os.path.basename(src))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
    else:                                     # 추출 텍스트
        base = os.path.splitext(name)[0] + ".md"
        dst = os.path.join(node_dir, "info", "md", base)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, "w", encoding="utf-8").write(text)
    return os.path.relpath(dst, node_dir)


def _ingest_vector(node_dir, doc_id, source_rel, text, embedder):
    import vectorstore
    chunks = vectorstore.chunk_text(text)
    if not chunks:
        return "vector(empty)"
    vecs = embedder.embed(chunks)
    store = vectorstore.VectorStore(os.path.join(node_dir, "info", "vector", "store.db"), embedder.dim)
    store.add_chunks(doc_id, source_rel, chunks, vecs)
    n = store.count(); store.close()
    return "info/vector/store.db (+%d chunks, total %d)" % (len(chunks), n)


def _load_embedder():
    sys.path.insert(0, _LIB)
    import embedder as emb
    return emb.get_embedder(backend=os.environ.get("HARNESS_EMBED_BACKEND", "local"),
                            model=os.environ.get("HARNESS_EMBED_MODEL", "BAAI/bge-m3"))


def run(node_dir, md_max, vector_min, dry_run):
    inbox = os.path.join(node_dir, "data", "update")
    if not os.path.isdir(inbox):
        print("[router] no inbox: %s" % inbox, file=sys.stderr); return 1
    files = sorted(os.path.join(inbox, f) for f in os.listdir(inbox)
                   if os.path.isfile(os.path.join(inbox, f)) and not f.startswith("."))
    if not files:
        print("[router] inbox empty"); return 0
    embedder = None
    archive_dir = os.path.join(node_dir, "archives")
    os.makedirs(archive_dir, exist_ok=True)

    for src in files:
        name = os.path.basename(src)
        ext = os.path.splitext(src)[1].lower()
        size = os.path.getsize(src)

        # 텍스트 확보(힌트/분류기/길이 판단용): plain 읽기, 문서 추출, 그 외 None
        text = None
        if ext in extractor.PLAIN:
            text = open(src, encoding="utf-8", errors="replace").read()
        elif ext not in STRUCTURED and extractor.is_supported(src):
            text, note = extractor.extract(src)
            if text is None:
                print("[router] %-28s [skip] 추출 불가: %s (inbox 유지)" % (name, note)); continue

        route, why = routing.decide(src, text, size, md_max, vector_min)
        # route 가 sql 인데 정형 파일이 아니면 wiki(md)로 강등
        if route == "sql" and ext not in STRUCTURED:
            route, why = "wiki", why + "→wiki(비정형)"
        print("[router] %-28s -> %s (%s)" % (name, route, why))
        if dry_run:
            continue

        if route == "sql":
            loc = _ingest_sql(src, node_dir); store = "sql"
        elif route == "rag":
            if text is None:
                text = open(src, encoding="utf-8", errors="replace").read()
            if embedder is None: embedder = _load_embedder()
            loc = _ingest_vector(node_dir, name, os.path.relpath(src, node_dir), text, embedder)
            store = "vector"
        else:  # wiki — Phase 1: md(raw). 추출 텍스트면 <name>.md, plain 이면 원본 복사
            loc = _write_md(node_dir, name, text=text) if text is not None else _write_md(node_dir, name, src=src)
            store = "md"

        res = provenance.record(node_dir, entry_id=name, store=store, location=loc.split(" ")[0],
                                source=src, tool="router@%s" % __tool_version__,
                                route=route, route_by=why)
        print("           %s -> %s [route=%s]" % (res["status"], loc, route))
        shutil.move(src, os.path.join(archive_dir, name))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--node", required=True)
    ap.add_argument("--md-max", type=int, default=8000)
    ap.add_argument("--vector-min", type=int, default=8000)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    sys.exit(run(a.node, a.md_max, a.vector_min, a.dry_run))


if __name__ == "__main__":
    main()
