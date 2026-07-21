---
title: 글로벌 시스템 프롬프트 (모든 에이전트 공통)
version: 0.2.0
status: living
---
# 모든 에이전트가 따르는 공통 규칙

1. 기판 MCP(`harness-<node>`)가 연결되어 있으면 작업 시작 시 **`begin_session(agent, ticket?)`을
   먼저** 호출한다. 반환된 `onboarding`을 이력 인계로 쓰고, 쓰기 도구용 `session_token`을 유지한다.
   MCP가 없으면 대상 노드의 `history/ONBOARDING.md`를 직접 읽는다.
2. 코드 작성은 `conventions/coding/`을 먼저 읽고 plan → verify → implement.
3. 위험 행동은 `platform/policies/approval-gates.md`의 게이트를 통과한다.
   **git push / force-push / 원격 쓰기**는 유저가 **"push" / "올려" / "push해" /
   "force-push"** 같이 **명시적 push 동사**로 승인한 뒤에만 한다.
   "커밋 보이게", "이력 남기기", "형상관리", "remote에 보이게" 등은 **push 승인이 아니다**
   — `git log`로 보여 주고 로컬에 둔다. `request_approval`만으로는 부족하고, 채팅에서
   사람의 명확한 승인을 기다린다.
4. 사실/데이터는 MCP `search_info`/`wiki_*`/`query_sql`/`get_provenance` 또는 `info/`에서 가져오고,
   출처는 `info/index.yaml`로 확인·인용한다.
5. 비자명한 결정은 `history/adr/`(`record_decision`)에, 진행 경과는 `history/worklog/<티켓>.md`
   (`append_worklog`)에 기록한다 — 채팅만으로는 이력이 남지 않는다.
6. 시크릿은 이름으로만 참조한다(`platform/policies/secrets.md`).
7. 스킬/커맨드 정본은 `platform/skills|commands/`이며, 활성 하네스 경로(`.claude/`·`.cursor/` 등)로
   투영된다. 관련 작업이면 해당 `SKILL.md`/커맨드 MD를 읽고 따른다(ADR 0009·0019).
8. 커밋/PR에 AI·도구 시그니처를 넣지 않는다(`Co-Authored-By` / `Made-with` /
   `Generated with …` 금지). 하네스 설정으로 주입을 끄고(`CONTRIBUTING.md`),
   메시지 본문에도 직접 추가하지 않는다. `--trailer Co-authored-by:…` 도 쓰지 않는다.
9. **로컬 throwaway 브랜치 → Jira feature 브랜치**로 옮길 때는 merge 하지 말고
   **cherry-pick 또는 rebase onto** 로 옮겨, 개별 커밋이 Jira 브랜치에 보이게 한다
   (merge 커밋으로 이력을 가리지 말 것). 티켓 작업 커밋 subject는
   `SW-<number> <summary>`(영어).
10. 하네스 전용 경로(`.cursor/rules/*.mdc`, `.claude/` 설정 등)에만 운영 규칙을 두지
    않는다. **모든 하네스가 읽는 정본은 `AGENTS.md`**(진실원본
    `platform/prompts/global-system.md` + `platform/policies/`)다. Cursor/Claude/Gemini
    어디든 동일하게 적용되어야 하는 규칙은 정본에 쓴 뒤 `harness gen-rules`로 투영한다.
