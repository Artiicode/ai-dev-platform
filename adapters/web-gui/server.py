#!/usr/bin/env python3
"""web-gui 백엔드 (스켈레톤) — 브라우저 채팅 UI ↔ 노드 기판.

새 데이터 계층 없음: mcp/server.py 의 동일 도구(list_info/search_info/query_sql/read_md/
get_provenance)를 재사용한다. stdlib http.server 만 사용(추가 의존성 0).

실행: NODE_DIR=projects/<name>-node python adapters/web-gui/server.py [--port 8800]
또는: harness webgui <name> [--port 8800]

엔드포인트:
  GET  /              채팅 UI(index.html)
  GET  /api/info      list_info()
  POST /api/search    {query,k}  -> search_info
  POST /api/query     {sql}      -> query_sql
  POST /api/chat      {message}  -> RAG 컨텍스트 조립 (+ LLM relay: 키 있으면 호출, 없으면 스텁)
"""
from __future__ import annotations
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
NODE_DIR = os.environ.get("NODE_DIR", os.getcwd())
sys.path.insert(0, os.path.join(ROOT, "mcp"))
sys.path.insert(0, os.path.join(ROOT, "tools", "lib"))
os.environ.setdefault("NODE_DIR", NODE_DIR)
import server as mcp_tools  # mcp/server.py — NODE_DIR 를 import 시점에 읽음


def _chat(message):
    """RAG: 노드에서 관련 컨텍스트 검색 → (키 있으면) 모델 답변, 없으면 컨텍스트+안내 반환."""
    hits = mcp_tools.search_info(message, 4)
    ctx = "\n".join("- (%s) %s" % (h.get("doc_id"), h.get("text", "")[:200])
                    for h in hits if "error" not in h)
    # 벤더 무관 relay: models.yaml 의 'coder' 역할이 설정+키 있으면 LiteLLM 경유 호출.
    try:
        import llm  # tools/lib (provider 무관)
        if llm.role_available("coder"):
            resp = llm.complete("coder", [
                {"role": "system", "content": "이 노드의 도우미. 아래 컨텍스트만 근거로 간결히 답하라."},
                {"role": "user", "content": "컨텍스트:\n%s\n\n질문: %s" % (ctx, message)}],
                max_tokens=800)
            m = resp.choices[0].message
            ans = getattr(m, "content", None) or (m.get("content") if isinstance(m, dict) else str(m))
            return {"answer": ans, "context": hits, "via": "litellm"}
    except Exception as e:
        return {"answer": "(LLM 호출 실패: %s) 검색 컨텍스트만 반환합니다." % e,
                "context": hits, "via": "error"}
    return {"answer": "(LLM relay 미연결: models.yaml 의 역할/키 설정 시 모델 답변. 지금은 RAG 컨텍스트만 표시)",
            "context": hits, "via": "stub"}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):  # 조용히
        pass

    def _send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if "json" in ctype or "html" in ctype else ""))
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _body(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            return self._send(200, open(os.path.join(HERE, "index.html"), "rb").read(), "text/html")
        if self.path == "/api/info":
            return self._send(200, mcp_tools.list_info())
        self._send(404, {"error": "not found"})

    def do_POST(self):
        try:
            d = self._body()
            if self.path == "/api/search":
                return self._send(200, mcp_tools.search_info(d.get("query", ""), int(d.get("k", 5))))
            if self.path == "/api/query":
                return self._send(200, mcp_tools.query_sql(d.get("sql", ""), d.get("db")))
            if self.path == "/api/chat":
                return self._send(200, _chat(d.get("message", "")))
            self._send(404, {"error": "not found"})
        except Exception as e:
            self._send(500, {"error": "%s: %s" % (type(e).__name__, e)})


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=int(os.environ.get("HARNESS_WEBGUI_PORT", 8800)))
    ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args()
    print("[web-gui] node=%s  http://%s:%d" % (NODE_DIR, a.host, a.port))
    ThreadingHTTPServer((a.host, a.port), H).serve_forever()


if __name__ == "__main__":
    main()
