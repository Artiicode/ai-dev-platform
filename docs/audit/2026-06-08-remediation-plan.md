---
title: 수정 계획 (Remediation Plan)
date: 2026-06-08
platform_version: ai-autodev-harness-v0.6.0
status: proposed
audience: [human, ai-agent]
related: [docs/audit/2026-06-08-conformance-audit.md, docs/ARCHITECTURE.md]
---

# 수정 계획

[적합성 감사](2026-06-08-conformance-audit.md) 결과에 대한 수정 로드맵. 사용자 결정사항을 설계 원칙으로 반영:

> **핵심 원칙(사용자 확정):** AI 모델·하네스(Cursor/Claude 등) 의존성은 기본적으로 0.
> API_KEY가 주어지거나 유저가 모델을 *명시*할 때만 그 의존성을 부착한다. 어떤 AI Agent가 와도
> "무슨 프로젝트인지·사용법·규칙"을 자동 인지할 수 있는 상태를 항상 유지한다.

## 1. 강제성 설계 — 의존성 계층화 (Dependency-Tiered Enforcement)

강제성을 단일 메커니즘이 아니라 **의존성 계층**으로 구현한다. 외부 AI를 프롬프트로 100% 강제하는
것은 불가능하므로, 진짜 강제는 **기계적 경계**에 둔다.

| 계층 | 의존성 | 역할 | 활성 조건 |
|---|---|---|---|
| **① 진입 규칙 파일 + git/CI 훅** | **0 (모델·하네스 무관)** | 어떤 에이전트가 봐도 프로젝트·사용법·규칙 자동 인지. 산출물은 훅이 기계적으로 검증/거부 | **항상** |
| **② MCP 쓰기 게이트웨이** | MCP 지원 하네스에서만 | 기판 *변경*을 도구 경계에서 게이팅(스키마/provenance/승인/시크릿) | 하네스가 MCP 지원 시 |
| **③ 모델 SDK (LiteLLM)** | API_KEY·모델 명시 시에만 | 실제 추론 실행 | 키/모델 지정 시 |

- **①만 항상 켜진다** = 사용자가 원한 "의존성 0 강제". ②③은 *조건부 부착*.
- ②의 "쓰기 게이트웨이": 기판 변경의 유일한 정식 경로를 MCP/CLI로 만들고, 쓰기 도구
  (`ingest_data`/`append_worklog`/`record_decision`/`request_approval`/`deploy`) 내부에서 규칙을
  강제. 직접 FS 쓰기는 ①의 git/CI 훅이 사후 검증으로 잡는다(이중 안전망).

## 2. 모델 무관성 — LiteLLM (사용자 확정)

- 최신 대안 점검 결과 Python 환경에서 LiteLLM이 여전히 표준(100+ provider, env API_KEY 기반 thin
  layer)이며 "키 있을 때만 의존성" 철학에 부합. 호스티드 게이트웨이(OpenRouter 등)는 외부 서비스
  의존을 새로 만들므로 보류.
- `models.yaml` 스키마는 이미 LiteLLM 스타일 → **실행층(`tools/lib/llm.py` 등)만 추가**하면 됨.
  키 부재 시 해당 역할 비활성(graceful), 임베딩은 기존 local/hash 유지.

## 3. 우선순위별 작업 (Phases)

### Phase 0 — 즉시 수정(저위험, 신뢰 회복)
- [ ] **B1** `bootstrap/install.py`가 `code/` 하위 전 파일 복사하도록 수정 → project_A에 `verify.yaml` 생성
- [ ] **B3** `ARCHITECTURE.md`(0.1.0→0.6.0), `USAGE.md`(0.5.0→0.6.0) 버전 동기화 + 릴리스 시 버전 일치 검사 추가
- [ ] **B5** `scenario/debug/` 용도 문서화 또는 제거(`debug.md`로 일원화)
- [ ] **B4** project_A 데모 인제스트 1회 실행해 `archives/`·`index.yaml` 채움(파이프라인 실증)

### Phase 1 — ① 보편 강제층 (최우선, 의존성 0)
- [ ] **단일 진실원본 → 진입 규칙 파일 생성기** `tools/gen_agent_rules.py`:
      `global-system.md` + 노드 규칙에서 `CLAUDE.md`/`AGENTS.md`/`.cursorrules`/`GEMINI.md`/
      `.github/copilot-instructions.md`를 *생성*. 루트(플랫폼) + 노드 양쪽.
- [ ] **git pre-commit 훅 + CI 검증** `tools/validate_node.py`:
      노드 구조 위반, `repo/`에 AI파일 혼입, worklog 미갱신, 평문 시크릿, 스키마 위반을 **거부**.
- [ ] **B2** `jsonschema`로 manifest/info-index 로드시 검증 (install/router/MCP 진입점)

### Phase 2 — ② MCP 쓰기 게이트웨이
- [ ] `begin_session(project)` 도구: 규칙 전문 + 세션 토큰 반환
- [ ] 쓰기 도구 추가(`ingest_data`/`append_worklog`/`record_decision`/`request_approval`/`deploy`),
      각 도구 내부에서 스키마·provenance·승인 게이트·시크릿 정책 강제
- [ ] 쓰기 도구는 세션 토큰 요구. `approval.py`를 MCP 경로에도 연결(현재 CLI 전용)

### Phase 3 — ③ 모델 무관성(LiteLLM) + data→info 완성
- [ ] `tools/lib/llm.py`: LiteLLM 래퍼. `models.yaml` 역할→호출, 키 부재 시 graceful 비활성
- [ ] `models.yaml`에 openai/google/ollama 예시 역할 추가 + 비-Claude 1종 스모크 테스트
- [ ] 변환기 **등록 메커니즘**(라우터 플러그인화) + `code/`·`docs/` 변환기 실제 구현 + 미지 확장자 명시적 처리

### Phase 4 — 마무리
- [ ] **B7** `schema_version` 마이그레이션 패턴 + `harness_min_version` 체크 코드
- [ ] **B6** 학습 커리큘럼 Lesson 2+(실습: MCP 호출/서브에이전트/검증) 작성
- [ ] 전 과정 ADR 기록 + CHANGELOG 갱신 + VERSION 범프

## 4. 검증 기준(Done의 정의)

- ① 임의 신규 에이전트가 노드를 열었을 때, 하네스가 규칙 파일을 자동 로드하고 git 훅이
  규칙 위반 커밋을 실제로 거부함을 시연.
- ② MCP 쓰기 도구가 세션 토큰·승인 없이 호출 시 거부됨을 시연.
- ③ `ANTHROPIC_API_KEY` 없이 다른 provider 키만으로 planner/coder 역할이 동작.

## 5. 미결 질문(진행 중 사용자 확인 필요)

- ①의 git 훅 강제: 모든 노드 `repo/`에 훅 자동 설치 vs CI 전용 검증 중 선호?
- ② 쓰기 게이트웨이 도입 시, 직접 FS 쓰기를 "정책 위반"으로 완전 금지할지, 훅 사후검증만 둘지?
