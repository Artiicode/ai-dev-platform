# 0017. 위키 v2 — 분류(type) facet + [[링크]] 그래프 질의 + 외부 항목 import

- status: accepted
- date: 2026-06-15
- related: ADR 0016(공유 지식), ADR 0010(라우팅 v2), ADR 0002(substrate+MCP)

## Context

위키가 평면 `info/wiki/<slug>.md` 였다(분류 없음, 자동 INDEX 평면, dangling 리포트만). 동료의 위키
(523 파일, ELS 2.0 규제 문서)는 **카테고리 폴더**(hardware/jira/risk/regulatory/requirements…) +
**그래프(neo4j) 질의** + **외부 소스 sync**(Jira 티켓·PR 이력 1급 페이지)로 운영된다. 비교 결과 우리
강점(벡터 검색·provenance·공유 페더레이션)은 유지하되 다음을 차용할 가치가 있었다: 분류 축, 그래프
질의, 외부 항목 1급화, 사람용 문서맵. 평면 구조는 수백 페이지에서 탐색·범위지정이 무너지고
`slugify` 60자 절단으로 슬러그 충돌(조용한 덮어쓰기) 위험도 있다.

## Decision

평면 검색 코어는 유지하고 **facet·그래프·import 를 더하는 하이브리드**.

- **type facet**: 위키 프론트매터에 `type`(hardware/requirements/risk/regulatory/test/ticket/pr/image/
  general). **폴더 계층이 아니라 facet** — 교차 주제를 한 폴더에 가두지 않고 `[[링크]]` 다차원 그래프를
  유지하기 위함. ingest 가 파일명/내용으로 자동추론, 에이전트는 `wiki_upsert(type=)` 로 지정.
  `INDEX.md` 는 type별 그룹(사람용 문서맵), 큐레이션 `SSOT.md` 는 자동생성이 보존(엔티티에서 제외).
  검색은 `type` 으로 facet 한정(`search_info`/`search_all`/`harness search --type`).
- **[[링크]] 그래프 질의**: `tools/lib/wiki_graph.py`(stdlib) — neighbors/backlinks/orphans/path(BFS)/
  summary/JSON export. **neo4j 미채용**: 데이터(`[[링크]]`)는 이미 있고 노드 규모에선 인메모리로 충분.
  `harness wiki --graph|--neighbors|--path|--orphans|--export`, MCP `wiki_graph`.
- **외부 항목 import(소스 비종속)**: `tools/data-to-info/import_items.py` — JSON/TSV(티켓/PR) →
  key/status/url 프론트매터 type 위키 페이지 + 임베딩 + provenance. 실제 fetch 는 소스 도구(Jira MCP·
  `gh`)가 JSON 을 떨궈주고 importer 가 소비. `harness import <node> <file> --type ticket`.

## Consequences

- 수백 페이지에서도 type별 탐색·범위지정이 되고, 검색(recall)과 facet(정밀 범위)이 상호보완한다.
- 추적성(요구사항↔리스크↔티켓)을 `[[링크]]` 그래프로 따라갈 수 있다 — 무거운 그래프 DB 없이.
- 외부 소스가 1급 위키 자산이 된다(소스 비종속이라 Jira/GitHub 외에도 동일 경로).
- 정직한 한계: type 자동추론은 휴리스틱(키워드)이라 완벽하지 않다 — 에이전트/사람이 교정한다.
- **향후 확장 경로(GraphRAG/온톨로지):** 본 구조가 그 기반이다. `wiki_graph.export_json` 의 (nodes,
  edges) 가 곧 지식그래프이고, `type` 은 온톨로지 클래스의 씨앗, `[[링크]]` 는 관계다. 데이터가 커져
  관계추론·multi-hop 질의가 중요해지면 같은 export 를 그래프 스토어(neo4j/kuzu)나 GraphRAG 인덱서에
  태우는 **어댑터만 추가**하면 된다(현 검색/provenance 불변). 임계 신호: 페이지 수천+·다중도메인 교차
  질의·관계기반 답변 비중↑. 그 전까지는 벡터+facet+경량그래프가 비용대비 최적.
