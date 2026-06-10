# 0010. data→info 라우팅 v2 (의미적 route + 힌트/분류기/폴백, md→wiki 로드맵)

- status: accepted (Phase 1–3 구현 완료)
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
- **Phase 2(완료):** `wiki` = 자기유지 엔티티 위키. `tools/lib/wiki.py`(결정적 저장/임베딩/링크) — route=wiki
  시 소스별 페이지 1차 적재 + 벡터 임베딩(검색 일원화). **'지능'(개념 분할·병합)은 구동 에이전트가 담당**
  (키 불필요): MCP `wiki_list/read/links/upsert`·`harness wiki`·`/update-reference` 로 병합/중복제거/`[[links]]`.
  store=wiki 추가(스키마). 키 기반 자동 병합(LLM 역할)은 후속 옵션.
- **Phase 3(완료):** 하이브리드 검색 `search_all` — 벡터(위키+RAG, kind 태그) + 질의어 매칭 SQL 테이블/컬럼
  힌트(결정적; 정확값은 query_sql 후속). `harness search` 표시 갱신.
- **옵션(구현):** `harness wiki-compile` — LLM 역할(키) 있을 때 위키 페이지 무인 자동 병합, 없으면 graceful
  no-op(에이전트 수동, 키 불필요). `tools/lib/wiki_compile.py`.

## Consequences

- 종류 기반 분배로 정확도↑, 힌트로 사용자가 명시 제어 가능. 분류기는 옵트인(키)이라 중립성 유지.
- Phase 2 위키는 LLM 필요 → 키 없는 환경은 raw md 로 graceful degrade.
- 엔티티 단위/슬러그 규칙, 위키-벡터 중복 처리는 Phase 2 착수 시 확정.
