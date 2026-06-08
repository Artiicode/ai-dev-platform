# 0008. 강제성: 의존성 계층화 (Dependency-Tiered Enforcement)

- status: accepted
- date: 2026-06-08
- related: docs/audit/2026-06-08-conformance-audit.md, docs/audit/2026-06-08-remediation-plan.md, ADR 0002

## Context

플랫폼 요구사항 중 핵심은 "타 AI Agent(Cursor/Gemini/API 등 임의 하네스)에게 규칙의 **강제성**을
주입"하는 것이다. 그러나 적합성 감사 결과 강제성이 사실상 미구현이었다 — `global-system.md`,
`ONBOARDING.md`, 정책은 전부 *평문 문서*였고, MCP 서버는 읽기 전용·무게이트, 승인 게이트는 CLI
흐름에서만 동작했다. 임의의 외부 에이전트는 규칙을 무시하고 진행할 수 있었다.

추가 제약(사용자 확정): **AI 모델·하네스 의존성은 기본 0.** API_KEY가 있거나 유저가 모델을 명시할
때만 그 의존성을 부착한다. 동시에 어떤 AI가 와도 프로젝트를 이해하고 사용법을 알 수 있어야 한다.

## Decision

외부 AI를 프롬프트로 100% 강제하는 것은 불가능하므로, 강제성을 **단일 메커니즘이 아니라 의존성
계층**으로 구현한다. 진짜 강제는 **기계적 경계(artifact boundary)** 에 둔다.

- **① 보편층 (의존성 0, 항상 켜짐).** 단일 진실원본(`platform/prompts/global-system.md`)에서
  하네스별 진입 규칙 파일(`CLAUDE.md`/`AGENTS.md`/`GEMINI.md`/`.cursorrules`/Copilot)을 *생성*
  (`tools/gen_agent_rules.py`) → 어떤 에이전트든 세션 시작 시 규칙을 자동 주입받는다. 산출물은
  `tools/validate_node.py`가 pre-commit + CI(`.github/workflows/validate.yml`) 두 곳에서 검증해
  규칙 위반을 **거부**한다. 직접 FS 쓰기는 허용하되 위반은 훅이 **사후** 거부(사용자 확정 ② 정책).
- **② MCP 쓰기 게이트웨이 (MCP 지원 하네스에서만).** 기판 변경의 정식 경로를 MCP/CLI로 두고,
  `begin_session`이 규칙 전문 + 토큰을 발급, 쓰기 도구(`append_worklog`/`record_decision`/
  `ingest_data`/`request_approval`)는 토큰을 요구하며 호출 시점에 provenance·이력·시크릿 정책을 강제.
- **③ 모델 SDK (키/모델 명시 시에만).** `tools/lib/llm.py`(LiteLLM)가 `models.yaml` 역할을 해석.
  키가 없으면 역할은 '비활성'이며 임의 프로바이더로 폴백하지 않는다. 평소엔 litellm 을 import 조차
  하지 않아 의존성 0을 유지한다.

①만 항상 동작하고 ②③은 조건부로 부착된다 — 이것이 "기본 의존성 0, 명시 시에만 부착" 원칙의 구현이다.

## Consequences

- 보편적 강제는 git/CI 훅이 담당하므로 하네스 종류와 무관하게 동작한다(honor-system 탈피).
- MCP 게이트웨이는 고충실도 강제를 주지만 MCP 비지원 하네스에는 적용되지 않는다 → ①이 바닥을 받친다.
- git 미초기화 상태에서는 pre-commit이 없으므로 CI가 필수 백스톱이다(`install-hooks`는 git init 후).
- 토큰은 프로세스 메모리(노드당 서버 1개) — 다중 서버/영속 세션이 필요해지면 state/ 영속화로 확장.
- 후속: repo/ 청결 검사 정교화, ingest 외 info/ 직접쓰기 차단 강화, worklog 갱신 누락 검출.
