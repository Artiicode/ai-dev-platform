---
description: 특정 프로젝트 노드의 직전 작업 이력(ONBOARDING)을 현재 세션에 인계받기.
argument-hint: <node>
---
유저가 새 세션에서 특정 노드의 이전 작업 맥락을 이어가려 할 때 호출한다(이력 인계는 수동 = 유저가 칠 때만).

대상 노드: `$ARGUMENTS` (비어 있으면 어떤 노드인지 유저에게 먼저 물어본다)

절차:
1. `python tools/harness_cli.py onboard $ARGUMENTS` 를 실행해 ONBOARDING.md 를 최신화한다.
2. `projects/$ARGUMENTS-node/history/ONBOARDING.md` 를 Read 로 읽는다.
3. 활성 티켓·최근 ADR·미해결(known issues)·최근 repo 커밋·verify 결과를 요약해 유저에게 보고하고,
   "이 맥락으로 이어서 진행할까요?"라고 확인한다.
4. 더 깊은 맥락이 필요하면 해당 노드의 `history/worklog/<티켓>.md` 를 추가로 읽는다.

이 명령은 자동 주입이 아니라 **유저 트리거 pull** 이다 — 호출 전까지 세션은 노드 이력을 모른다(의도된 동작).
