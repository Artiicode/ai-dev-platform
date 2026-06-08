#!/usr/bin/env python3
"""data-to-info router — data/update/* 를 특성 기반으로 md/sql/vector 로 실제 적재.

라우팅 (ARCHITECTURE §6):
  - 정형(.json/.csv/.tsv)                 -> sql    (info/db/<name>.sqlite)  예: 로봇암 x,y,z
  - 문서(.pdf/.docx/.html/.img/.md/.txt)  -> 추출 후 텍스트 길이로:
        길면(>=vector_min) -> vector (info/vector/store.db, sqlite-vec)
        짧으면(<md_max)    -> md     (info/md/<name>[.md])
  - 추출 불가(라이브러리 부재 등)         -> skip + 사유 보고 (원본은 inbox 유지)

동작: 적재 → provenance 기록 → 원본 archives/ 이동(멱등: 동일 sha skip).
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

__tool_version__ = "0.2.0"

STRUCTURED = {".json", ".csv", ".tsv"}


def decide_store(path, md_max, vector_min):
    ext = os.path.splitext(path)[1].lower()
    if ext in STRUCTURED:
        return "sql"
    if ext in extractor.PLAIN:
        return "vector" if os.path.getsize(path) >= vector_min else "md"
    if extractor.is_supported(path):
        return "extract"   # pdf/docx/html/img — 추출 후 길이로 재결정
    return "md"


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
        store = decide_store(src, md_max, vector_min)
        print("[router] %-28s -> %s" % (name, store))
        if dry_run:
            print("           (dry-run)"); continue

        # 1) 정형 -> SQL
        if store == "sql":
            loc = _ingest_sql(src, node_dir)
        else:
            # 2) 문서 -> 추출 후 길이로 md/vector
            if store == "extract":
                text, note = extractor.extract(src)
                if text is None:
                    print("           [skip] 추출 불가: %s (원본 inbox 유지)" % note); continue
                target = "vector" if len(text) >= vector_min else "md"
                print("           extracted(%s, %d chars) -> %s" % (note, len(text), target))
                if target == "md":
                    loc = _write_md(node_dir, name, text=text)
                else:
                    if embedder is None: embedder = _load_embedder()
                    loc = _ingest_vector(node_dir, name, os.path.relpath(src, node_dir), text, embedder)
                store = target
            elif store == "md":            # plain, 작음
                loc = _write_md(node_dir, name, src=src)
            elif store == "vector":        # plain, 큼
                text = open(src, encoding="utf-8", errors="replace").read()
                if embedder is None: embedder = _load_embedder()
                loc = _ingest_vector(node_dir, name, os.path.relpath(src, node_dir), text, embedder)
            else:
                print("           [skip] unknown"); continue

        res = provenance.record(node_dir, entry_id=name, store=store, location=loc.split(" ")[0],
                                source=src, tool="router@%s" % __tool_version__)
        print("           %s -> %s" % (res["status"], loc))
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
