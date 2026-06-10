# 0011. 기본 임베딩 모델: Qwen3-Embedding-0.6B (대안 bge-m3)

- status: accepted
- date: 2026-06-10
- related: ADR 0003(local-embeddings), 메모리 llm-wiki-routing-refs

## Context

기존 기본 임베딩은 bge-m3. 더 나은 로컬 모델이 있는지 2026 기준 리서치 + 실문서 비교를 수행.
리서치: Qwen3-Embedding 계열이 MTEB 다국어 1위(8B=70.58), 한국어 포함 다국어 강점. 8B/4B 는 GPU·
차원(2560/4096) 부담 → 로컬/CPU/오프라인 기본인 우리 환경엔 **Qwen3-Embedding-0.6B(1024차원)** 가 적합
(우리 벡터스토어 float[1024] 드롭인). bge-m3 는 MIT·100+언어·hybrid(dense+sparse+multivector).

## 실측 (실문서: 13p 영문 코딩표준 PDF, 동일 6질의, sqlite-vec)

- bge-m3 vs Qwen3-0.6B(plain 쿼리): 영문에서 **대등**, 결정적 우열 없음.
- Qwen3-0.6B 는 **쿼리 instruction**("Instruct: ...\nQuery: ...") 적용 시 향상 — naming→Code Style, comments
  →@brief, header→5.4 등 관련 청크가 상위로. instruction 없이는 손해(비대칭 인코딩 필요).
- 종합: 영문 대등~약간 우위 + **다국어/한국어 명확 우위** + 더 가벼움(~1.2GB vs ~2GB) + instruction-tuned.

## Decision

기본 임베딩을 **Qwen/Qwen3-Embedding-0.6B** 로 변경. **bge-m3 는 대안**으로 유지(`HARNESS_EMBED_MODEL=BAAI/bge-m3`).
embedder 에 **비대칭 인코딩** 도입: 문서(passage)는 plain, 쿼리는 `embed_query`(Qwen 류는 instruction
프리픽스 자동, bge·hash 는 무프리픽스). 검색 경로(MCP `search_info`)가 `embed_query` 사용. 둘 다 1024차원이라
스토어 스키마 변경 없음.

## Consequences

- 다국어(특히 한국어) 검색 품질↑, 다운로드↓. 로컬/오프라인/CPU 원칙 유지(hash 폴백 그대로).
- 모델 교체 시 해당 노드 벡터스토어는 같은 모델로 재생성 필요(`harness rebuild`) — 벡터 공간이 다르므로.
- bge-m3 의 hybrid(sparse/multivector) 가 필요한 경우 대안으로 선택 가능.
- 한국어 실자료로 재평가 시 Qwen 우위가 더 뚜렷할 것으로 예상(영문 테스트는 보수적 하한).
