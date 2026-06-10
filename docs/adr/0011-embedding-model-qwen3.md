# 0011. 기본 임베딩 모델: bge-m3 (대안 Qwen3-Embedding-0.6B) — 한국어 실측 기반

- status: accepted (0.15.0 에서 Qwen 으로 변경 → 0.16.0 에서 한국어 실측 후 bge-m3 로 환원)
- date: 2026-06-10
- related: ADR 0003(local-embeddings), 메모리 llm-wiki-routing-refs

## Context

더 나은 로컬 임베딩이 있는지 2026 리서치 + 실측. MTEB 다국어 리더보드는 Qwen3-Embedding **8B** 가 1위지만
8B/4B 는 GPU·비(非)1024차원이라 로컬/CPU/오프라인 기본인 우리 환경엔 부적합. CPU 구동 가능한 후보는
**Qwen3-Embedding-0.6B(1024차원)** 와 기존 **bge-m3(MIT, 1024, hybrid)**.

## 실측

1) 영문 코딩표준 PDF(13p) 6질의: 둘이 대등(무승부). → 이것만 보고 0.15.0 에서 기본을 Qwen 으로 성급 변경.
2) **한국어 KorQuAD v1.0**(80문단/100질의, 질문→정답문단 검색):

   | 모델 | R@1 | R@3 | R@5 | MRR |
   |---|---|---|---|---|
   | **BAAI/bge-m3** | **0.850** | **0.980** | **1.000** | **0.913** |
   | Qwen3-Embedding-0.6B (쿼리 instruction 적용) | 0.750 | 0.960 | 0.990 | 0.853 |

   → **bge-m3 가 전 지표 우세**. Qwen 은 instruction 을 적용했음에도 0.6B(최소형)라 한국어 retrieval 에서 밀림.

## Decision

기본 임베딩을 **BAAI/bge-m3** 로 (환원·)확정. **Qwen3-Embedding-0.6B 는 대안**(`HARNESS_EMBED_MODEL`).
embedder 의 **비대칭 인코딩**(문서 plain / 쿼리 `embed_query`, Qwen 류 instruction 자동)은 **유지** —
Qwen 을 대안으로 쓸 때 필요하고 bge/hash 엔 무해(프리픽스 없음).

## Consequences

- 교훈: **리더보드 순위(특히 대형 모델 기준)를 소형 모델·실제 언어/도메인에 일반화하지 말 것.** 실측이 뒤집었다.
- 한국어/다국어 retrieval 은 bge-m3 가 강함(MIT·hybrid sparse/multivector도 이점). 둘 다 1024차원이라 교체 자유,
  단 교체 시 노드 벡터스토어 `harness rebuild` 재생성 필요(벡터공간 상이).
- GPU 가용 환경에서 Qwen3 **8B**(또는 더 큰 다국어 모델)는 더 나을 수 있으나 본 플랫폼 기본(로컬/CPU)엔 부적합.
  표본이 작아(80/100) 추가 검증 여지는 있으나 4개 지표 일관되게 bge 우세.
