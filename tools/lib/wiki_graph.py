"""wiki_graph — `[[link]]` 그래프 질의(neo4j 없이 stdlib).

위키 페이지의 `[[링크]]` 를 방향 그래프로 보고 이웃·백링크·고아·경로를 질의한다. 데이터는 이미
`info/wiki/*.md` 에 있으므로 별도 저장 없이 매번 빌드한다(노드 규모에선 충분히 빠름). JSON export 로
외부 그래프 도구(원하면 neo4j 등)에 넣을 수도 있다.
"""
from __future__ import annotations
import json
import os

import wiki  # same dir (tools/lib)


def build(node_dir):
    """Return {nodes: {slug: {title, type, out:[slugs], in:[slugs]}}, edges: [[a,b]]}.
    Edges point page -> linked page (by slugified [[link]] target)."""
    slugs = wiki.list_pages(node_dir)
    nodes = {}
    for s in slugs:
        pg = wiki.read(node_dir, s) or {}
        fm = pg.get("frontmatter") or {}
        nodes[s] = {"title": fm.get("entity", s), "type": fm.get("type", "uncategorized"),
                    "out": [], "in": []}
    edges = []
    for s in slugs:
        pg = wiki.read(node_dir, s) or {}
        for link in pg.get("links") or []:
            tgt = wiki.slugify(link)
            nodes[s]["out"].append(tgt)
            edges.append([s, tgt])
            if tgt in nodes:                       # backlink only for existing targets
                nodes[tgt]["in"].append(s)
    return {"nodes": nodes, "edges": edges}


def neighbors(node_dir, slug):
    g = build(node_dir)
    n = g["nodes"].get(slug)
    if not n:
        return {"error": "페이지 없음: %s" % slug}
    return {"slug": slug, "out": sorted(set(n["out"])), "in": sorted(set(n["in"]))}


def orphans(node_dir):
    """Pages with no incoming and no outgoing links (isolated — likely need [[linking]])."""
    g = build(node_dir)
    return sorted(s for s, n in g["nodes"].items() if not n["out"] and not n["in"])


def dangling(node_dir):
    """[[links]] pointing to non-existent pages (target slug not among pages)."""
    g = build(node_dir)
    pages = set(g["nodes"])
    out = {}
    for a, b in g["edges"]:
        if b not in pages:
            out.setdefault(a, []).append(b)
    return {a: sorted(set(v)) for a, v in out.items()}


def path(node_dir, src, dst):
    """Shortest [[link]] path src->dst (BFS over outgoing edges); [] if unreachable."""
    g = build(node_dir)
    if src not in g["nodes"] or dst not in g["nodes"]:
        return []
    from collections import deque
    seen, q = {src}, deque([[src]])
    while q:
        p = q.popleft()
        if p[-1] == dst:
            return p
        for nxt in g["nodes"][p[-1]]["out"]:
            if nxt in g["nodes"] and nxt not in seen:
                seen.add(nxt)
                q.append(p + [nxt])
    return []


def export_json(node_dir, out_path=None):
    g = build(node_dir)
    out_path = out_path or os.path.join(wiki.wiki_dir(node_dir), "graph.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    open(out_path, "w", encoding="utf-8").write(json.dumps(g, ensure_ascii=False, indent=2))
    return os.path.relpath(out_path, node_dir)


def summary(node_dir):
    g = build(node_dir)
    types = {}
    for n in g["nodes"].values():
        types[n["type"]] = types.get(n["type"], 0) + 1
    return {"pages": len(g["nodes"]), "links": len(g["edges"]),
            "types": types, "orphans": orphans(node_dir),
            "dangling": dangling(node_dir)}


# Heuristic thresholds for the stack advisor. Honest defaults — tune per project.
# Rationale: vector+facet+light-graph is best until the corpus is both LARGE and
# RELATION-HEAVY (multi-hop / cross-domain answers). Only then does a graph DB /
# GraphRAG / ontology earn its operational cost (see ADR 0017).
_ADVISE = {"pages_big": 300, "density_rel": 2.0, "types_multi": 6,
           "types_ontology": 8, "orphan_ratio": 0.5}


def advise(node_dir):
    """Watch growth signals and recommend whether to keep vector+facet or graduate to a
    graph DB / GraphRAG / ontology. Advisory only — adoption stays a human decision."""
    g = build(node_dir)
    pages = len(g["nodes"])
    links = len(g["edges"])
    types = {}
    for n in g["nodes"].values():
        types[n["type"]] = types.get(n["type"], 0) + 1
    density = round(links / pages, 2) if pages else 0.0
    orps = orphans(node_dir)
    orphan_ratio = round(len(orps) / pages, 2) if pages else 0.0
    th = _ADVISE
    reasons, recs = [], []
    big = pages >= th["pages_big"]
    relational = density >= th["density_rel"]
    multi = len(types) >= th["types_multi"]
    if big and (relational or multi):
        recs.append("graph-db/GraphRAG")
        reasons.append("규모↑(%d페이지) + %s — 관계기반·multi-hop 질의 비중이 커짐. "
                       "wiki_graph.export_json → kuzu(임베디드) 또는 GraphRAG 어댑터 검토."
                       % (pages, "링크밀도 %.1f" % density if relational else "다중도메인 %d종" % len(types)))
    if len(types) >= th["types_ontology"]:
        recs.append("ontology")
        reasons.append("type %d종 — 통제어휘/스키마 검증이 이득. type→YAML 온톨로지(클래스+속성) 승격 검토."
                       % len(types))
    if orphan_ratio >= th["orphan_ratio"]:
        reasons.append("고아 비율 %.0f%% — 스택 확장보다 먼저 `[[링크]]`/type 정리 권장." % (orphan_ratio * 100))
    if not recs:
        recs.append("vector+facet (현행 유지)")
        reasons.append("현 규모/관계도에선 벡터+facet+경량그래프가 비용대비 최적. 임계 미달.")
    return {"pages": pages, "links": links, "density": density, "types": types,
            "orphan_ratio": orphan_ratio, "thresholds": th,
            "recommend": recs, "reasons": reasons}
