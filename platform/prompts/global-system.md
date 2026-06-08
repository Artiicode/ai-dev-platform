---
title: 글로벌 시스템 프롬프트 (모든 에이전트 공통)
version: 0.1.0
status: living
---
# 모든 에이전트가 따르는 공통 규칙

1. 작업 시작 전 대상 프로젝트의 `history/ONBOARDING.md`를 읽는다.
2. 코드 작성은 `code/coding_convention/`을 먼저 읽고 plan → verify → implement.
3. 위험 행동은 `platform/policies/approval-gates.md`의 게이트를 통과한다.
4. 사실/데이터는 `info/`에서 가져오고, 출처는 `info/index.yaml`로 확인·인용한다.
5. 비자명한 결정은 `history/adr/`에, 진행 경과는 `history/worklog/<티켓>.md`에 기록한다.
6. 시크릿은 이름으로만 참조한다(`platform/policies/secrets.md`).
