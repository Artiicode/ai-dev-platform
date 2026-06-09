# 0010. data→info 라우팅 v2 (의미적 route + 힌트/분류기/폴백, md→wiki 로드맵)

- status: accepted (Phase 1 구현)
- date: 2026-06-10
- related: ADR 0004(ingest), 메모리 llm-wiki-routing-refs

## Context

기존 라우터는 확장자(→sql) + 크기(→md/vector)만으로 분배했다. 자료의 *종류/의미*를 반영하지 못해
작아도 RAG가 맞는 문서, 커도 권위문서(md)인 경우를 오라우팅했다. 2026 합의: SQL=정형/정확,
RAG=대규모 비정형, md/LLM-Wiki=소~중 큐레이션·정확답. 하이브리드가 베스트프랙티스(메모리 참조).

## Decision

**의미적 route(sql|rag|wiki)** 를 도입하고, 결정 순서를 **힌트 → LLM 분류기 → 크기 폴백**으로 둔다.

- 힌트: 파일명 토큰 `.sql.`/`.rag.`/`.wiki.` 또는 텍스트 프론트매터 `route:`. (결정적·무비용·예측가능)
- 분류기: `models.yaml` role `classifier`(없으면 `coder`)가 활성일 때 내용 샘플로 판정. 키 없으면 생략.
- 폴백: 정형 확장자→sql, 큰 텍스트→rag, 작은→wiki. **모델 키 없이도 동작**(의존성 0 유지).
- `info/index.yaml` 에 `route`/`route_by` 기록(추적성). route→store 매핑(Phase 1): sql→sqlite, rag→vector,
  wiki→md(raw).

## Roadmap

- **Phase 1(완료):** 위 라우팅 + index 기록. `tools/data-to-info/routing.py`.
- **Phase 2:** `wiki` 를 Karpathy식 **자기유지 엔티티 위키**(개념별 페이지 + `[[links]]`, AI가 병합/중복제거,
  sha 멱등)로 격상. 위키 페이지도 임베딩해 벡터 검색에 포함(검색 일원화). 키 없으면 raw md 폴백.
- **Phase 3:** 하이브리드 검색(wiki+vector+sql 통합 조회·병합; SUQL/DSL 경량).

## Consequences

- 종류 기반 분배로 정확도↑, 힌트로 사용자가 명시 제어 가능. 분류기는 옵트인(키)이라 중립성 유지.
- Phase 2 위키는 LLM 필요 → 키 없는 환경은 raw md 로 graceful degrade.
- 엔티티 단위/슬러그 규칙, 위키-벡터 중복 처리는 Phase 2 착수 시 확정.
