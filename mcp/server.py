#!/usr/bin/env python3
"""ai-autodev-harness MCP 서버 (L3b 어댑터).

L2 기판(info/ 의 md·sql·vector + index.yaml)을 MCP 도구로 노출하는 *게이트웨이*다.
자체 데이터를 소유하지 않는다 — 파일/DB를 읽을 뿐. 어떤 MCP 지원 클라이언트(Claude 등)든
동일한 고충실도 접근(시맨틱 검색/SQL/출처)을 얻는다.

대상 노드: 환경변수 NODE_DIR (없으면 현재 디렉토리). 클라이언트는 프로젝트 노드마다
이 서버를 하나씩 띄운다.

읽기 도구:
  - list_info()                : 이 노드에서 사용 가능한 md/db/vector 요약
  - search_info(query, k)      : 벡터 RAG 시맨틱 검색 (로컬 임베딩)
  - query_sql(sql, db?)        : info/db/*.sqlite 읽기 전용 SQL
  - read_md(name)              : info/md/<name> 원문
  - get_provenance(entry_id?)  : info/index.yaml 출처 기록

쓰기 게이트웨이(강제성 ②) — 기판 변경의 정식 경로. 토큰 + 정책을 강제:
  - begin_session(agent, ticket?)          : 규칙 전문 + session_token 반환(핸드셰이크)
  - append_worklog(ticket, entry, token)   : 이력 append(시크릿 차단)
  - record_decision(title, body, token)    : ADR 기록
  - ingest_data(token, dry_run?)           : data/update → info/ (provenance/archives 자동)
  - request_approval(action, detail?)      : 위험행동 승인 요청(사람이 최종 승인)
직접 FS 쓰기도 가능하나 규칙 위반은 pre-commit/CI 훅이 사후 거부한다(② 정책).
"""
from __future__ import annotations
import datetime
import glob
import os
import secrets
import sqlite3
import sys

from mcp.server.fastmcp import FastMCP

NODE_DIR = os.environ.get("NODE_DIR", os.getcwd())
INFO = os.path.join(NODE_DIR, "info")
_LIB = os.path.join(os.path.dirname(__file__), "..", "tools", "lib")
_TOOLS = os.path.join(os.path.dirname(__file__), "..", "tools")
for _p in (_LIB, _TOOLS, os.path.join(_TOOLS, "data-to-info")):
    sys.path.insert(0, _p)

mcp = FastMCP("ai-autodev-harness")

_embedder = None
_SESSIONS = {}  # session_token -> {agent, ticket, started}  (프로세스 메모리; 노드당 서버 1개)


def _now():
    return datetime.datetime.utcnow().isoformat() + "Z"


def _rules_text():
    for cand in (os.path.join(NODE_DIR, "CLAUDE.md"),
                 os.path.join(NODE_DIR, "..", "..", "platform", "prompts", "global-system.md")):
        if os.path.exists(cand):
            return open(cand, encoding="utf-8").read()
    return "(규칙 파일 없음 — `python tools/gen_agent_rules.py` 실행 필요)"


def _secret_in(text):
    """평문 시크릿 패턴이면 설명 문자열, 아니면 None. validate_node 규칙 재사용."""
    try:
        import validate_node as vn
    except Exception:
        return None
    for ln in text.splitlines():
        if vn.SECRET_ALLOW.search(ln):
            continue
        for pat, desc in vn.SECRET_PATTERNS:
            if pat.search(ln):
                return desc
    return None


def _get_embedder():
    global _embedder
    if _embedder is None:
        import embedder as emb
        backend = os.environ.get("HARNESS_EMBED_BACKEND", "local")
        model = os.environ.get("HARNESS_EMBED_MODEL", "BAAI/bge-m3")
        _embedder = emb.get_embedder(backend=backend, model=model)
    return _embedder


def _load_index():
    p = os.path.join(INFO, "index.yaml")
    if not os.path.exists(p):
        return {"schema_version": 1, "entries": []}
    try:
        import yaml
        return yaml.safe_load(open(p)) or {"schema_version": 1, "entries": []}
    except Exception:
        import json
        return json.load(open(p))


@mcp.tool()
def list_info() -> dict:
    """이 노드에서 질의 가능한 정보 자산 요약(md 파일, sql 테이블, 벡터 청크 수)."""
    md = [os.path.basename(p) for p in glob.glob(os.path.join(INFO, "md", "*")) if os.path.isfile(p)]
    dbs = {}
    for dbp in glob.glob(os.path.join(INFO, "db", "*.sqlite")):
        con = sqlite3.connect(dbp)
        tbls = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        dbs[os.path.basename(dbp)] = tbls
        con.close()
    vec_path = os.path.join(INFO, "vector", "store.db")
    vec_chunks = 0
    if os.path.exists(vec_path):
        con = sqlite3.connect(vec_path)
        try:
            vec_chunks = con.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        except Exception:
            pass
        con.close()
    return {"node": NODE_DIR, "md_files": md, "sql_dbs": dbs, "vector_chunks": vec_chunks}


@mcp.tool()
def search_info(query: str, k: int = 5) -> list:
    """벡터 RAG 시맨틱 검색. 가장 관련 있는 청크를 출처(provenance)와 함께 반환."""
    import vectorstore
    vec_path = os.path.join(INFO, "vector", "store.db")
    if not os.path.exists(vec_path):
        return [{"error": "벡터 스토어 없음. 먼저 router 로 인제스트하세요."}]
    emb = _get_embedder()
    store = vectorstore.VectorStore(vec_path, emb.dim)
    qv = emb.embed([query])[0]
    hits = store.search(qv, k)
    store.close()
    return hits


@mcp.tool()
def query_sql(sql: str, db: str | None = None) -> dict:
    """info/db 의 정형 데이터에 읽기 전용 SQL. db 미지정 시 모든 *.sqlite 를 스키마로 ATTACH.

    예: query_sql("SELECT x,y,z FROM robot_arm LIMIT 5")
    읽기 전용 — SELECT/WITH/PRAGMA 만 허용.
    """
    head = sql.lstrip().split(None, 1)[0].lower() if sql.strip() else ""
    if head not in ("select", "with", "pragma"):
        return {"error": "읽기 전용: SELECT/WITH/PRAGMA 만 허용"}
    con = sqlite3.connect(":memory:")
    attached = []
    dbfiles = ([os.path.join(INFO, "db", db)] if db
               else glob.glob(os.path.join(INFO, "db", "*.sqlite")))
    for dbp in dbfiles:
        if not os.path.exists(dbp):
            return {"error": f"db 없음: {dbp}"}
        schema = "".join(c if c.isalnum() else "_" for c in os.path.splitext(os.path.basename(dbp))[0])
        con.execute(f"ATTACH DATABASE ? AS {schema}", (dbp,))
        attached.append(schema)
    try:
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description] if cur.description else []
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "attached_schemas": attached}
    finally:
        con.close()
    return {"columns": cols, "rows": rows, "attached_schemas": attached}


@mcp.tool()
def read_md(name: str) -> dict:
    """info/md/<name> 원문 반환(소량/권위 문서)."""
    path = os.path.join(INFO, "md", os.path.basename(name))
    if not os.path.exists(path):
        return {"error": f"없음: info/md/{name}"}
    return {"name": os.path.basename(name), "content": open(path, encoding="utf-8").read()}


@mcp.tool()
def get_provenance(entry_id: str | None = None) -> list:
    """info/index.yaml 출처 기록. entry_id 지정 시 해당 항목만."""
    entries = _load_index().get("entries", [])
    if entry_id:
        entries = [e for e in entries if e.get("id") == entry_id]
    return entries


# ── 쓰기 게이트웨이 (강제성 ②) ───────────────────────────────────────────────

@mcp.tool()
def begin_session(agent: str, ticket: str | None = None) -> dict:
    """작업 시작 핸드셰이크. 규칙 전문 + session_token 을 반환한다.
    쓰기 도구는 이 토큰을 요구하므로, 에이전트는 규칙을 받은 뒤에야 기판을 변경할 수 있다."""
    token = secrets.token_hex(16)
    _SESSIONS[token] = {"agent": agent, "ticket": ticket, "started": _now()}
    return {"session_token": token, "node": os.path.abspath(NODE_DIR), "rules": _rules_text(),
            "must": "쓰기 호출 시 session_token 전달. 위반 산출물은 커밋/CI 훅이 거부함."}


def _need_token(token):
    return token in _SESSIONS


@mcp.tool()
def append_worklog(ticket: str, entry: str, session_token: str) -> dict:
    """history/worklog/<ticket>.md 에 타임스탬프 경과를 append(이력 규칙 강제, 시크릿 차단)."""
    if not _need_token(session_token):
        return {"error": "유효한 session_token 필요 — 먼저 begin_session() 호출."}
    sec = _secret_in(entry)
    if sec:
        return {"error": "평문 시크릿 의심(%s) — 이름참조만 허용(secrets 정책)." % sec}
    wl = os.path.join(NODE_DIR, "history", "worklog")
    os.makedirs(wl, exist_ok=True)
    path = os.path.join(wl, "%s.md" % ticket)
    created = not os.path.exists(path)
    with open(path, "a", encoding="utf-8") as f:
        if created:
            f.write("---\nticket: %s\nstatus: in-progress\nupdated: %s\n---\n\n## 진행 로그 (append-only)\n"
                    % (ticket, _now()))
        f.write("\n- [%s] %s\n" % (_now(), entry))
    return {"ok": True, "path": os.path.relpath(path, NODE_DIR), "created": created}


@mcp.tool()
def record_decision(title: str, body: str, session_token: str) -> dict:
    """history/adr/ 에 비자명 결정을 기록(번호 자동 채번)."""
    if not _need_token(session_token):
        return {"error": "유효한 session_token 필요 — begin_session() 먼저."}
    sec = _secret_in(body)
    if sec:
        return {"error": "평문 시크릿 의심(%s)." % sec}
    adr = os.path.join(NODE_DIR, "history", "adr")
    os.makedirs(adr, exist_ok=True)
    n = len(glob.glob(os.path.join(adr, "[0-9]*.md"))) + 1
    slug = "".join(c if c.isalnum() else "-" for c in title.lower()).strip("-")[:40] or "decision"
    path = os.path.join(adr, "%04d-%s.md" % (n, slug))
    open(path, "w", encoding="utf-8").write("# %04d. %s\n\n- date: %s\n\n%s\n" % (n, title, _now(), body))
    return {"ok": True, "path": os.path.relpath(path, NODE_DIR)}


@mcp.tool()
def ingest_data(session_token: str, dry_run: bool = False) -> dict:
    """data/update/* → info/ (md/sql/vector) 정식 변환 경로. provenance/archives 자동 처리.
    info/ 에 직접 쓰지 말고 이 도구(또는 `harness ingest`)를 사용한다."""
    if not _need_token(session_token):
        return {"error": "유효한 session_token 필요."}
    import router
    rc = router.run(NODE_DIR, 8000, 8000, dry_run)
    return {"ok": rc in (0, None), "node": os.path.abspath(NODE_DIR), "dry_run": dry_run}


@mcp.tool()
def request_approval(action: str, detail: str = "") -> dict:
    """위험행동(ssh/scp/push/deploy/삭제) 승인 요청. 정책을 반환하고 state/ 에 대기 기록.
    MCP는 TTY가 없으므로 최종 승인은 사람이 한다."""
    pol = os.path.join(NODE_DIR, "..", "..", "platform", "policies", "approval-gates.md")
    policy = open(pol, encoding="utf-8").read() if os.path.exists(pol) else "(정책 파일 없음)"
    st = os.path.join(NODE_DIR, "state")
    os.makedirs(st, exist_ok=True)
    with open(os.path.join(st, "pending-approvals.md"), "a", encoding="utf-8") as f:
        f.write("- [%s] %s: %s\n" % (_now(), action, detail))
    return {"requires_human_approval": True, "action": action, "policy": policy}


if __name__ == "__main__":
    # 트랜스포트: stdio(기본, CLI/Claude Code) | sse | streamable-http (향후 웹 GUI)
    transport = os.environ.get("HARNESS_MCP_TRANSPORT", "stdio")
    mcp.run(transport=transport)
