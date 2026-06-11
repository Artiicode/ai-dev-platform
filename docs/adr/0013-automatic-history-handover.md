# 0013. 작업 이력 자동 인계 (ONBOARDING 자동 갱신 + 세션 인계)

- status: accepted
- date: 2026-06-11
- related: ADR 0006(onboarding/locks), ADR 0002(substrate+MCP), 0.17.2(유저 노드 미추적)

## Context

작업 이력(이슈·디버깅·시나리오·테스트 결과·결정)을, 작업이 끝난 뒤 새로 접근한 AI 에이전트가
이어볼 수 있어야 한다. 기존에 구조(`history/worklog`·`history/adr`·`history/ONBOARDING.md`·
`state/verify-report.md`)와 MCP 쓰기 도구(`begin_session`/`append_worklog`/`record_decision`)는
있었으나, "자동"이 아니었다:

1. `ONBOARDING.md`(큐레이션 브리프)는 **수동 `harness onboard`** 로만 갱신 → 로그가 쌓여도 브리프가
   낡아, 다음 에이전트가 옛 정보를 본다.
2. `begin_session` 이 **이전 이력을 반환하지 않음** → 새 에이전트가 ONBOARDING을 따로 찾아 읽어야 함.
3. 가장 풍부한 자동 이력원인 **repo 의 실제 git 커밋**(이슈/디버깅/기능이 커밋 메시지로 축적)과
   **verify 테스트 결과**가 브리프에 반영되지 않음.
4. 유저 노드는 우리 repo에서 미추적(0.17.2)이라, 우리 git 훅으로는 노드 이력을 큐레이션할 수 없다 —
   트리거가 MCP/CLI 쪽에 있어야 한다.

## Decision

**`ONBOARDING.md`를 "이력이 바뀌는 모든 지점"에서 자동 재생성하고, 세션 시작 시 에이전트에게
자동 인계한다. 브리프는 수기 로그뿐 아니라 repo 커밋·테스트 결과까지 자동 수집한다.**

- `gen_onboarding` 가 두 자동 이력원을 추가 수집:
  - **repo git 로그** — `git -C <node>/repo log --oneline -n 12`(심링크된 실제 프로젝트 이력).
  - **verify 결과** — `state/verify-report.md` 요약.
- 자동 갱신 트리거(수동 `harness onboard` 불필요):
  - MCP `append_worklog` / `record_decision` / `ingest_data` 직후 `_refresh_onboarding()`.
  - `harness verify` 가 리포트 기록 후 재생성.
- 자동 인계: MCP `begin_session` 이 최신 ONBOARDING을 재생성해 `onboarding` 필드로 반환 →
  새 에이전트가 핸드셰이크만으로 이전 이력(활성 티켓·결정·repo 커밋·테스트)을 받는다.
- 한계(정직): 에이전트가 worklog/ADR를 **쓰는** 것 자체는 결정론적으로 강제 불가(규칙으로 지시).
  단 repo 커밋·테스트 결과는 에이전트가 별도로 기록하지 않아도 자동 수집되므로, 최소 이력은 보장된다.

## Consequences

- 새 에이전트는 "매번" 최신 인계서를 자동으로 받는다 — 수동 `onboard` 의존 제거.
- worklog를 안 남긴 경우에도 repo 커밋/테스트 결과로 작업 맥락이 어느 정도 복원된다.
- 비용: 쓰기/검증/세션 시작당 브리프 1회 재생성(로컬 파일 + 짧은 git 호출). 무시 가능.
- 유저 노드 미추적 정책과 무관하게(트리거가 MCP/CLI라서) 동작한다.
