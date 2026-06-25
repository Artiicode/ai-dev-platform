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
import io
import json
import os
import shutil
import sqlite3
import sys

_LIB = os.path.join(os.path.dirname(__file__), "..", "lib")
sys.path.insert(0, _LIB)
import re          # noqa: E402
import provenance  # noqa: E402
import extractor   # noqa: E402
import routing     # noqa: E402  (sql|rag|wiki 결정: 힌트 → LLM 분류기 → 크기 폴백)
import wiki        # noqa: E402  (route=wiki → 엔티티 위키 페이지 + 임베딩)
import locks       # noqa: E402  (동시 ingest 차단: state/ingest.json)


# Filename/content → wiki type facet (Robert-style taxonomy, auto-inferred at ingest).
# First match wins; default "general". Agents can override via wiki_upsert(type=...).
_TYPE_HINTS = [
    ("requirements", ("requirement", "srs", "-req", "req-")),
    ("risk",         ("risk", "fmea", "fmeca", "fta", "hazard", "14971")),
    ("regulatory",   ("iec-", "iso-", "fda", "60601", "62304", "regulatory")),
    ("qms",          ("qms", "document-control", "change-control", "good-documentation")),
    ("test",         ("test", "verification", "validation", "-te-", "swta")),
    ("hardware",     ("hardware", "-hw", "schematic", "connectivity", "pinout", "eeprom")),
    ("ticket",       ("ticket", "jira", "-issue")),
    ("pr",           ("pr-", "pull-request", "pullrequest")),
]


def _infer_type(name, text):
    hay = (os.path.splitext(name)[0] + " " + (text or "")[:200]).lower()
    for t, keys in _TYPE_HINTS:
        if any(k in hay for k in keys):
            return t
    return "general"


def _title_for(name, text):
    """엔티티 제목: 텍스트의 첫 H1 우선, 없으면 파일명(힌트 토큰 제거)."""
    if text:
        for ln in text.splitlines():
            if ln.strip().startswith("# "):
                return ln.strip()[2:].strip()
    base = os.path.splitext(name)[0]
    base = re.sub(r"\.(sql|rag|wiki)$", "", base, flags=re.I)
    return base.replace("_", " ").replace("-", " ").strip() or base

__tool_version__ = "0.3.0"
STRUCTURED = routing.STRUCTURED


def _read_text(src):
    """텍스트를 인코딩 폴백으로 읽는다(UTF-8 → cp1252 → latin-1).
    Windows Excel CSV 등 비-UTF8 파일에서 UnicodeDecodeError 로 죽지 않게 한다."""
    raw = open(src, "rb").read()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


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
        rows = _rows_from_json(json.loads(_read_text(src)))
    else:
        delim = "\t" if ext == ".tsv" else ","
        rows = list(csv.DictReader(io.StringIO(_read_text(src)), delimiter=delim))
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


def _image_card(node_dir, src, name, text, sha):
    """Preserve the image as a local asset and return a deterministic wiki-card body that
    references it with ![](../assets/..). Agents open the asset with Read on demand — no
    vision captioning (offline, no cost). OCR text, when present, is appended below."""
    assets_dir = os.path.join(node_dir, "info", "assets")
    os.makedirs(assets_dir, exist_ok=True)                 # on-demand, like info/db
    asset_name = name
    dst = os.path.join(assets_dir, asset_name)
    if os.path.exists(dst) and provenance.sha256_of(dst) != sha:
        asset_name = "%s_%s" % (sha[:8], name)             # name clash, different bytes → unique
        dst = os.path.join(assets_dir, asset_name)
    shutil.copyfile(src, dst)                              # working copy; original still → archives/
    title = _title_for(name, text)
    lines = ["원본 파일: %s" % name, "",
             "![%s](../assets/%s)" % (title, asset_name), "",
             "> 이 이미지를 시각적으로 확인하려면 위 asset 경로를 Read 하라."]
    if text.strip():
        lines += ["", "## OCR 추출 텍스트", "", text.strip()]
    return "\n".join(lines) + "\n"


def _sanitize(s, fallback):
    out = "".join(c if c.isalnum() else "_" for c in str(s)).strip("_")
    return out or fallback


def _ingest_xlsx_tables(node_dir, base, sheets):
    """Tabular sheets → one sqlite per workbook (info/db/<base>.sqlite), a table per sheet.
    Returns [(sheet_title, table, columns, nrows, preview_rows)]. Numbers kept numeric."""
    db_path = os.path.join(node_dir, "info", "db", _sanitize(base, "book") + ".sqlite")
    tables, db, used = [], None, set()
    for sh in (s for s in sheets if s["tabular"]):
        header = sh["rows"][0]
        ncols = max((i + 1 for i, c in enumerate(header) if c is not None and str(c).strip()), default=0)
        cols = []
        for i in range(ncols):
            h = header[i] if i < len(header) else None
            cn = _sanitize(h if h is not None and str(h).strip() else "", "col%d" % (i + 1))
            while cn in cols:
                cn += "_"
            cols.append(cn)
        tname = _sanitize(sh["title"], "sheet")
        while tname in used:
            tname += "_"
        used.add(tname)
        if db is None:
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            db = sqlite3.connect(db_path)
        col_defs = ", ".join('"%s"' % c for c in cols)
        ph = ", ".join("?" for _ in cols)
        db.execute('DROP TABLE IF EXISTS "%s"' % tname)
        db.execute('CREATE TABLE "%s" (%s)' % (tname, col_defs))
        data = []
        for r in sh["rows"][1:]:
            vals = [(r[i] if i < len(r) else None) for i in range(ncols)]
            vals = [v if isinstance(v, (int, float)) or v is None else str(v) for v in vals]
            data.append(vals)
        db.executemany('INSERT INTO "%s" (%s) VALUES (%s)' % (tname, col_defs, ph), data)
        preview = [cols] + [["" if v is None else str(v) for v in row] for row in data[:5]]
        tables.append((sh["title"], tname, cols, len(data), preview))
    if db:
        db.commit(); db.close()
    return os.path.relpath(db_path, node_dir) if tables else None, tables


def _xlsx_card(name, db_rel, base, tables, text_sheets):
    """Discoverable wiki body: column names + small preview (vector recall) + query_sql pointer
    for exact values; free-form sheets inline as text."""
    L = ["원본 파일: %s (Excel)" % name, ""]
    if tables:
        L.append("## 표 시트 → SQL (정확값은 `query_sql` 로 조회)")
        for title, tname, cols, n, preview in tables:
            L.append("- 시트 `%s` → db=`%s` table=`%s` (%d행) · columns: %s"
                     % (title, os.path.basename(db_rel), tname, n, ", ".join(cols)))
            L.append("  " + " | ".join(cols))
            for row in preview[1:]:
                L.append("  " + " | ".join(row))
        L.append("")
        L.append("> 정확한 값/집계는 위 테이블을 `query_sql` 로 조회하라(미리보기는 일부 행).")
    for sh in text_sheets:
        L += ["", "## %s" % sh["title"]]
        L += [" | ".join("" if c is None else str(c).strip() for c in r) for r in sh["rows"]]
    return "\n".join(L).strip() + "\n"


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
                            model=os.environ.get("HARNESS_EMBED_MODEL", emb.DEFAULT_MODEL))


def run(node_dir, md_max, vector_min, dry_run):
    inbox = os.path.join(node_dir, "data", "update")
    if not os.path.isdir(inbox):
        print("[router] no inbox: %s" % inbox, file=sys.stderr); return 1
    files = sorted(os.path.join(inbox, f) for f in os.listdir(inbox)
                   if os.path.isfile(os.path.join(inbox, f)) and not f.startswith("."))
    if not files:
        print("[router] inbox empty"); return 0
    archive_dir = os.path.join(node_dir, "archives")
    os.makedirs(archive_dir, exist_ok=True)

    # Dry-run only reads — no lock. A real ingest mutates info/ + moves originals to
    # archives/, so guard it with a node-scoped ingest lock: a second concurrent ingest
    # over the same inbox would race (file moved out from under it → FileNotFoundError).
    # A dead holder's lock is auto-reclaimed (PID/TTL) by locks.acquire.
    owner = None
    if not dry_run:
        owner = "ingest:%d" % os.getpid()
        try:
            locks.acquire(node_dir, owner=owner, scope="ingest", name="ingest", ttl=21600)
        except locks.LockError as e:
            print("[router] 동시 ingest 차단 — 다른 실행이 진행 중: %s" % e, file=sys.stderr)
            print("         (끝나길 기다리거나, 죽은 프로세스면 자동 회수 후 재시도하세요)", file=sys.stderr)
            return 2

    try:
        return _process(node_dir, files, archive_dir, md_max, vector_min, dry_run)
    finally:
        if owner:
            try:
                locks.release(node_dir, owner, name="ingest")
            except Exception:
                pass


def _process(node_dir, files, archive_dir, md_max, vector_min, dry_run):
    embedder = None
    for src in files:
        name = os.path.basename(src)
        ext = os.path.splitext(src)[1].lower()
        size = os.path.getsize(src)

        # Excel: hybrid per-sheet — tabular sheets → SQL tables(정확), free-form → text; plus one
        # discoverable wiki index (columns + preview + query_sql pointer). Multi-output, so handled
        # here rather than the single-route path below.
        if ext in extractor.XLSX:
            sheets, note = extractor.xlsx_sheets(src)
            if not sheets:
                print("[router] %-28s [skip] %s (inbox 유지)" % (name, note)); continue
            ntab = sum(1 for s in sheets if s["tabular"])
            print("[router] %-28s -> sql+wiki (xlsx: 표 %d/%d시트)" % (name, ntab, len(sheets)))
            if dry_run:
                continue
            base = os.path.splitext(name)[0]
            db_rel, tables = _ingest_xlsx_tables(node_dir, base, sheets)
            text_sheets = [s for s in sheets if not s["tabular"]]
            body = _xlsx_card(name, db_rel, base, tables, text_sheets)
            sha = provenance.sha256_of(src)
            res_w = wiki.upsert(node_dir, title=_title_for(name, ""), body=body,
                                type=_infer_type(name, body), sources=[{"id": name, "sha256": sha}])
            if embedder is None:
                embedder = _load_embedder()
            wiki.embed_page(node_dir, res_w["slug"], embedder)
            wiki.reindex(node_dir)
            # One schema-valid provenance entry (store/route enums). The wiki card is the discoverable
            # entry and lists the SQL db/tables/columns + a query_sql pointer; tables also surface via
            # search_all. (provenance.record dedups by source+sha, so two entries for one xlsx isn't
            # possible anyway.) route_by keeps the xlsx origin + table count.
            provenance.record(node_dir, entry_id=name, store="wiki", location=res_w["path"],
                              source=src, tool="router@%s" % __tool_version__,
                              route="wiki", route_by="xlsx:%dtab" % ntab)
            print("           tables=%s · wiki=%s" % ([t[1] for t in tables], res_w["slug"]))
            try:
                shutil.move(src, os.path.join(archive_dir, name))
            except FileNotFoundError:
                print("           [skip] 원본이 이미 이동됨: %s" % name, file=sys.stderr)
            continue

        # 텍스트 확보(힌트/분류기/길이 판단용): plain 읽기, 문서 추출, 그 외 None
        text = None
        if ext in extractor.PLAIN:
            text = open(src, encoding="utf-8", errors="replace").read()
        elif ext in extractor.IMAGE:
            # Images are never skipped: best-effort OCR, but preserve the asset + a wiki card
            # even with no recognizable text (drawings/photos, or no OCR engine installed).
            text, _ = extractor.extract(src)
            text = text or ""
        elif ext not in STRUCTURED and extractor.is_supported(src):
            text, note = extractor.extract(src)
            if text is None:
                print("[router] %-28s [skip] 추출 불가: %s (inbox 유지)" % (name, note)); continue

        if ext in extractor.IMAGE:
            route, why = "wiki", "image"          # always a referenceable wiki card (skip classifier)
        else:
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
        else:  # wiki — 엔티티 위키 페이지(소스별 1개) + 벡터 임베딩. 병합/[[링크]]는 에이전트가 후처리.
            if text is None:
                text = open(src, encoding="utf-8", errors="replace").read()
            sha = provenance.sha256_of(src)
            is_img = ext in extractor.IMAGE
            body = _image_card(node_dir, src, name, text, sha) if is_img else text
            wtype = "image" if is_img else _infer_type(name, text)
            res_w = wiki.upsert(node_dir, title=_title_for(name, text), body=body,
                                type=wtype, sources=[{"id": name, "sha256": sha}])
            if embedder is None: embedder = _load_embedder()
            nch = wiki.embed_page(node_dir, res_w["slug"], embedder)
            wiki.reindex(node_dir)
            loc = res_w["path"]; store = "wiki"
            print("           wiki page %s (+%d chunks 임베딩)" % (res_w["slug"], nch))

        res = provenance.record(node_dir, entry_id=name, store=store, location=loc.split(" ")[0],
                                source=src, tool="router@%s" % __tool_version__,
                                route=route, route_by=why)
        print("           %s -> %s [route=%s]" % (res["status"], loc, route))
        try:
            shutil.move(src, os.path.join(archive_dir, name))
        except FileNotFoundError:
            # Defense in depth: original already moved (interrupted/raced run). Skip.
            print("           [skip] 원본이 이미 이동됨: %s" % name, file=sys.stderr)
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
