# 0018. 워크트리는 노드 하위 worktree/ 에 — 하나의 공유 노드 허브

- status: accepted
- date: 2026-06-16
- related: ADR 0015(노드 메타 git), ADR 0006(locks/worktree), ADR 0017(위키)

## Context

브랜치별 작업 격리를 `git worktree` 로 한다. 기존엔 워크트리를 `<node>/state/wt-<branch>` 에 만들었는데
두 문제가 있었다:

1. **node-git 오염.** node `.gitignore` 는 `state/lock.json`·`state/ingest.json` 만 무시했고
   `state/wt-*`(워크트리=코드 체크아웃)는 무시하지 않아, 워크트리의 코드가 노드 메타 git 에 추적·흡수됐다.
2. **개념 불명확.** 워크트리가 런타임 상태 폴더(`state/`)에 묻혀 있어, "브랜치마다 노드를 들고 다니는 것"처럼
   보였다. 실제로 원하는 모델은 **노드 1개(공유 허브) + 그 안에 브랜치별 코드 체크아웃**이다.

## Decision

**워크트리를 `<node>/worktree/<branch>/` 로 옮기고, node-git 이 `/worktree` 를 무시한다.**

- `harness worktree <node> --branch B` → `<node>/worktree/<B>/` 에 `git worktree add`(repo 의 브랜치 체크아웃).
- node `.gitignore` 에 `/worktree` 추가(`/repo` 와 동일 취지: 외부 코드, 노드 메타 아님).
- `resolve_node` 가 경로를 받으면 상위로 올라가 노드 루트를 찾는다 → 워크트리 안에서 `harness <cmd>` 를
  실행해도 그 하나의 노드로 resolve.

**공유/비공유 경계:**
- **공유(노드 1벌):** `info/`·`context/`·`history/`·`scenario/`·`conventions/`·`skills/`·`data/` — 모든
  워크트리가 같은 것을 본다(MCP `NODE_DIR`=노드 루트). 브랜치를 바꿔도 지식·이력·규약은 일관.
- **비공유(브랜치별):** `repo/`(primary)·`worktree/<B>`(코드 체크아웃). 브랜치마다 다른 게 당연(워크트리 목적).

## Consequences

- 워크트리 코드가 더는 노드 메타 git 에 흡수되지 않는다(오염·비대 제거). `validate_node` 의 repo 흡수
  불변식과 같은 맥락.
- 브랜치별로 노드(컨텍스트/이력)를 복제하지 않으므로 드리프트가 없다 — 한 곳만 업데이트.
- 기존 `state/wt-*` 워크트리는 자동 이전하지 않는다: `git worktree move` 또는 제거 후 재생성으로 옮긴다.
- 정직한 한계: 동시에 여러 워크트리가 같은 노드 `state/`(락/ingest)를 쓰므로, 쓰기 작업(ingest 등)은
  노드 단위 락(ADR 0006)으로 직렬화된다 — 코드는 병렬, 기판 쓰기는 직렬.
