# ADR 0003 — 로컬 임베딩(bge-m3) + sqlite-vec, 이슈트래킹 로컬 기본
- 상태: accepted · 날짜: 2026-06-08
## 맥락
RAG가 필요하나 오프라인/데이터 주권/비용을 고려. 외부 의존 최소화 선호.
## 결정
- 임베딩: 로컬 bge-m3(sentence-transformers) 기본. 모델 부재 시 결정적 hash 폴백으로 강등(파이프라인 무중단).
- 벡터 스토어: sqlite-vec(단일 파일 DB, info/vector/store.db). 의존성 최소·git 운영 친화.
- 이슈 트래킹: 로컬 history/worklog + adr 기본. 필요 시 Linear/Jira/GitHub Issues 를 MCP로 연동(나중에).
## 결과
오프라인 동작 보장, 노드별 자족적 벡터 스토어. backend/model 은 env(HARNESS_EMBED_*)로 교체 가능.
