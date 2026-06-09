"""routing — 자료를 sql | rag | wiki 로 라우팅 결정 (라우팅 v2, Phase 1).

결정 순서(사용자 확정):
  1) 힌트:   파일명 토큰 `.sql.`/`.rag.`/`.wiki.`  또는 텍스트 프론트매터 `route: sql|rag|wiki`
  2) 분류기: LLM(role classifier→coder, 키 있을 때) 이 내용 샘플로 종류 판정
  3) 폴백:   확장자(정형→sql) + 크기(큰 텍스트→rag, 작은→wiki)  ← 모델 키 없어도 동작

의미적 route 와 물리 store 매핑(Phase 1): sql→sql, rag→vector, wiki→md(raw).
(Phase 2 에서 wiki→엔티티 위키 페이지로 격상 예정.)
"""
from __future__ import annotations
import os, re, sys

_LIB = os.path.join(os.path.dirname(__file__), "..", "lib")
sys.path.insert(0, _LIB)

STRUCTURED = {".json", ".csv", ".tsv"}
ROUTES = ("sql", "rag", "wiki")
_HINT_RE = re.compile(r"\.(sql|rag|wiki)\.", re.I)
_FM_ROUTE = re.compile(r"^route:\s*(sql|rag|wiki)\s*$", re.I | re.M)


def hint(path, text):
    """파일명 토큰 또는 프론트매터 route: — 명시 힌트(최우선)."""
    m = _HINT_RE.search(os.path.basename(path).lower())
    if m:
        return m.group(1).lower()
    if text:
        s = text.lstrip()
        if s.startswith("---"):
            parts = s.split("---", 2)
            if len(parts) >= 3:
                mm = _FM_ROUTE.search(parts[1])
                if mm:
                    return mm.group(1).lower()
    return None


def classify(name, ext, text):
    """LLM 분류기. role classifier(없으면 coder)가 활성일 때만; 아니면 None."""
    try:
        import llm
    except Exception:
        return None
    role = None
    for r in ("classifier", "coder"):
        try:
            if llm.role_available(r):
                role = r; break
        except Exception:
            pass
    if not role:
        return None
    sample = (text or "")[:1500]
    prompt = (
        "다음 자료를 어디에 저장할지 한 단어로만 답하라: sql | rag | wiki\n"
        "- sql:  숫자·표·정형(행/열, 키-값), 정확 질의/집계 대상\n"
        "- rag:  길고 비정형인 문서, 의미검색용\n"
        "- wiki: 작고 권위있는 개념/사실(통째로 읽어도 부담 없는 정리지식)\n"
        "파일명: %s (확장자 %s)\n내용 샘플:\n%s\n답(sql/rag/wiki):" % (name, ext, sample))
    try:
        resp = llm.complete(role, [{"role": "user", "content": prompt}], max_tokens=4)
        m = resp.choices[0].message
        ans = (getattr(m, "content", None) or (m.get("content") if isinstance(m, dict) else "") or "").strip().lower()
        for r in ROUTES:
            if r in ans:
                return r
    except Exception:
        return None
    return None


def fallback(ext, text, size, md_max, vector_min):
    if ext in STRUCTURED:
        return "sql"
    if text is not None:
        return "rag" if len(text) >= vector_min else "wiki"
    return "rag" if size >= vector_min else "wiki"   # 추출 전(크기로)


def decide(path, text, size, md_max, vector_min):
    """(route, route_by) 반환. route ∈ {sql,rag,wiki}, route_by ∈ {hint,classifier,fallback}."""
    h = hint(path, text)
    if h:
        return h, "hint"
    ext = os.path.splitext(path)[1].lower()
    c = classify(os.path.basename(path), ext, text)
    if c:
        return c, "classifier"
    return fallback(ext, text, size, md_max, vector_min), "fallback"
