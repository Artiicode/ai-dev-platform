"""wiki — 자기유지 엔티티 위키 저장소 (LLM Wiki 패턴, 결정적/무LLM).

`info/wiki/<slug>.md` 엔티티 페이지(개념당 1개) + `[[wiki-links]]` + `INDEX.md`.
'지능'(어떤 개념으로 쪼개고 병합할지)은 구동 에이전트(Claude 등)나 LLM 역할이 담당하고,
이 모듈은 결정적 저장/임베딩/링크검사만 제공한다(키 불필요).

페이지 프론트매터: entity, slug, sources:[{id,sha256}], updated. 본문에 [[다른개념]] 으로 링크.
벡터 검색 일원화: 각 페이지를 doc_id="wiki:<slug>" 로 벡터 스토어에 임베딩(검색이 위키+RAG 동시).
"""
from __future__ import annotations
import datetime, os, re

_LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def _now():
    return datetime.datetime.utcnow().isoformat() + "Z"


def slugify(title: str) -> str:
    s = re.sub(r"[^0-9A-Za-z가-힣]+", "-", (title or "").strip().lower()).strip("-")
    return s[:60] or "untitled"


def wiki_dir(node_dir: str) -> str:
    return os.path.join(node_dir, "info", "wiki")


def page_path(node_dir: str, slug: str) -> str:
    return os.path.join(wiki_dir(node_dir), slug + ".md")


def list_pages(node_dir: str):
    d = wiki_dir(node_dir)
    if not os.path.isdir(d):
        return []
    return sorted(f[:-3] for f in os.listdir(d)
                  if f.endswith(".md") and f != "INDEX.md")


def read(node_dir: str, slug: str):
    p = page_path(node_dir, slug)
    if not os.path.exists(p):
        return None
    raw = open(p, encoding="utf-8").read()
    fm, body = {}, raw
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            try:
                import yaml
                fm = yaml.safe_load(parts[1]) or {}
            except Exception:
                fm = {}
            body = parts[2].lstrip("\n")
    return {"slug": slug, "frontmatter": fm, "body": body, "links": sorted(set(_LINK_RE.findall(raw)))}


def extract_links(text: str):
    return sorted(set(_LINK_RE.findall(text or "")))


def upsert(node_dir: str, *, title: str, body: str, sources=None, slug: str = None) -> dict:
    """엔티티 페이지 생성/덮어쓰기(결정적). 병합 판단은 호출자(에이전트/LLM)가 한 뒤 완성본을 넘긴다."""
    slug = slug or slugify(title)
    os.makedirs(wiki_dir(node_dir), exist_ok=True)
    srcs = sources or []
    try:
        import yaml
        fm = yaml.safe_dump({"entity": title, "slug": slug, "sources": srcs, "updated": _now()},
                            allow_unicode=True, sort_keys=False).strip()
    except Exception:
        fm = "entity: %s\nslug: %s\nupdated: %s" % (title, slug, _now())
    b = re.sub(r"^#\s+.*\n+", "", body.strip(), count=1)  # 본문 선두 H1 제거(제목 중복 방지)
    out = "---\n%s\n---\n\n# %s\n\n%s\n" % (fm, title, b)
    open(page_path(node_dir, slug), "w", encoding="utf-8").write(out)
    return {"slug": slug, "path": os.path.relpath(page_path(node_dir, slug), node_dir),
            "links": extract_links(body)}


def delete(node_dir: str, slug: str) -> bool:
    """페이지 + 해당 벡터 doc 제거(병합 시 중복 페이지 정리용)."""
    p = page_path(node_dir, slug)
    existed = os.path.exists(p)
    if existed:
        os.remove(p)
    try:
        import vectorstore
        vp = os.path.join(node_dir, "info", "vector", "store.db")
        if os.path.exists(vp):
            st = vectorstore.VectorStore(vp, 1024); st.delete_doc("wiki:%s" % slug); st.close()
    except Exception:
        pass
    return existed


def link_report(node_dir: str) -> dict:
    """[[link]] 가 실제 페이지로 연결되는지 — dangling(미연결) 목록 반환."""
    pages = set(list_pages(node_dir))
    dangling = {}
    for slug in pages:
        miss = [ln for ln in read(node_dir, slug)["links"] if slugify(ln) not in pages]
        if miss:
            dangling[slug] = miss
    return {"pages": sorted(pages), "dangling": dangling}


def reindex(node_dir: str) -> str:
    """INDEX.md 재생성(엔티티 목록 + 링크 요약)."""
    pages = list_pages(node_dir)
    lines = ["# 위키 인덱스 (자동 생성 — `harness wiki --reindex`)", ""]
    for slug in pages:
        pg = read(node_dir, slug)
        title = (pg["frontmatter"] or {}).get("entity", slug)
        links = ", ".join("[[%s]]" % l for l in pg["links"]) if pg["links"] else "-"
        lines.append("- [[%s]] (`%s.md`) → %s" % (title, slug, links))
    if not pages:
        lines.append("(아직 엔티티 페이지 없음)")
    out = "\n".join(lines) + "\n"
    os.makedirs(wiki_dir(node_dir), exist_ok=True)
    open(os.path.join(wiki_dir(node_dir), "INDEX.md"), "w", encoding="utf-8").write(out)
    return os.path.relpath(os.path.join(wiki_dir(node_dir), "INDEX.md"), node_dir)


def embed_page(node_dir: str, slug: str, embedder) -> int:
    """페이지 본문을 벡터 스토어에 임베딩(doc_id=wiki:slug). 검색 일원화."""
    import vectorstore
    pg = read(node_dir, slug)
    if not pg:
        return 0
    chunks = vectorstore.chunk_text(pg["body"])
    if not chunks:
        return 0
    store = vectorstore.VectorStore(os.path.join(node_dir, "info", "vector", "store.db"), embedder.dim)
    store.add_chunks("wiki:%s" % slug, "info/wiki/%s.md" % slug, chunks, embedder.embed(chunks))
    store.close()
    return len(chunks)


def embed_all(node_dir: str, embedder) -> int:
    return sum(embed_page(node_dir, s, embedder) for s in list_pages(node_dir))
