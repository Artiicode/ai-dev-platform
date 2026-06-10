"""wiki_compile — (옵션) 키 기반 위키 자동 병합.

models.yaml 에 LLM 역할(classifier→coder)이 설정+키 있을 때, 현재 엔티티 위키 페이지들을 LLM 이 검토해
같은 개념을 하나로 병합·중복제거·[[링크]]한다(무인). 키 없으면 graceful no-op — 구동 에이전트가
MCP `wiki_upsert` 로 수동 병합(기본·키불필요 경로). 결정적 저장/임베딩은 tools/lib/wiki.py 가 담당.
"""
from __future__ import annotations
import json, os, sys

_LIB = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _LIB)


def _role():
    try:
        import llm
    except Exception:
        return None, None
    for r in ("classifier", "coder"):
        try:
            if llm.role_available(r):
                return llm, r
        except Exception:
            pass
    return llm, None


def auto_merge(node_dir: str) -> dict:
    import wiki
    llm, role = _role()
    pages = [wiki.read(node_dir, s) for s in wiki.list_pages(node_dir)]
    pages = [p for p in pages if p]
    if not pages:
        return {"status": "empty", "msg": "위키 페이지 없음."}
    if not role:
        return {"status": "no-llm",
                "msg": "LLM 역할 미설정 — 에이전트가 MCP wiki_upsert 로 수동 병합하세요(키 불필요 경로)."}

    catalog = "\n".join("## %s (slug=%s)\n%s" % ((p["frontmatter"] or {}).get("entity", p["slug"]),
                                                 p["slug"], p["body"][:800]) for p in pages)
    prompt = (
        "아래는 엔티티 위키 페이지들이다. 같은 개념은 하나로 병합하고 중복을 제거하라.\n"
        "JSON 배열만 출력: [{\"entity\":\"제목\",\"slugs\":[병합할 기존 slug들],\"body\":\"병합 마크다운"
        "(관련개념은 [[제목]] 으로 링크)\"}]. 병합 불필요한 페이지는 결과에 넣지 마라.\n\n" + catalog)
    try:
        resp = llm.complete(role, [{"role": "user", "content": prompt}], max_tokens=2000)
        m = resp.choices[0].message
        raw = getattr(m, "content", None) or (m.get("content") if isinstance(m, dict) else "") or ""
        plan = json.loads(raw[raw.find("["): raw.rfind("]") + 1])
    except Exception as e:
        return {"status": "error", "msg": "LLM 병합 계획 파싱 실패: %s" % e}

    applied = []
    for g in plan:
        slugs = [s for s in g.get("slugs", []) if wiki.read(node_dir, s)]
        if not slugs or not g.get("entity") or not g.get("body"):
            continue
        srcs = []
        for s in slugs:
            srcs.extend((wiki.read(node_dir, s)["frontmatter"] or {}).get("sources", []) or [])
        res = wiki.upsert(node_dir, title=g["entity"], body=g["body"], sources=srcs)
        for s in slugs:
            if s != res["slug"]:
                wiki.delete(node_dir, s)
        applied.append(res["slug"])
    if applied:
        import router
        emb = router._load_embedder()
        wiki.embed_all(node_dir, emb)
        wiki.reindex(node_dir)
    return {"status": "merged", "role": role, "entities": applied}
