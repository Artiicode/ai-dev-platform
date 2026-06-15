# 0015. 노드 메타 자체 git — 에이전트가 자동 관리, repo/ 는 외부 객체

- status: accepted
- date: 2026-06-15
- related: ADR 0013(자동 이력 인계), ADR 0008(강제성), ADR 0004(ingest/init)

## Context

노드의 AI 운영 데이터(context/scenario/history/info/manifest)는 시간에 따라 진화하는 자산인데
**버전관리가 없었다**. 플랫폼 repo 는 `/projects/*` 를 무시하므로(ADR 0009 — clone 이 upstream 과
동일하게 유지) 노드 변경 이력이 어디에도 남지 않았다.

옵션을 검토했다:
- **submodule**: 플랫폼이 노드의 특정 커밋을 핀으로 고정. 그러나 공개 템플릿에 개인 노드 포인터가
  박히고(철학 충돌), detached HEAD·2단계 커밋 등 운영 부담이 크다.
- **subtree**: 노드 이력이 플랫폼 history 에 병합 — "프로젝트별 독립 이력"이라는 목표와 정반대.

또한 `repo/`(실제 프로젝트 코드)는 자체 repo(별도 origin)에서 관리되는 **외부 객체**다. 노드 이력이
이 코드를 흡수하면 안 된다.

## Decision

**노드는 자기 자신의 git 을 가진다(`projects/<name>-node/.git`). 에이전트가 자동·강제로 관리하고,
`repo/` 는 노드 git 이 추적하지 않는다.**

- `tools/node/node_git.py`: `ensure_repo`(init + `.gitignore` + 초기 커밋, 멱등), `commit`(변경 시만),
  `repo_tracked`(불변식 검사). `.gitignore` 는 항상 `/repo`(외부 코드) + 재생성물(vector 바이너리)·
  시크릿·캐시를 제외하고, archives/info(wiki·md·db·index)는 추적 → 노드가 자체 git 으로 재현 가능.
- **자동 생성**: `harness init`/`bootstrap` 이 노드 git 을 만든다.
- **자동 커밋**: `harness ingest`/`onboard`/`verify` 와 MCP 쓰기(worklog/ADR/wiki/standup/ingest)가
  변경을 노드 git 에 커밋(best-effort, 도구 실패 안 시킴). 직접 편집분은 `harness save <node> -m`.
- **강제(게이트)**: `validate_node.py` 가 `repo/` 가 노드 git 에 추적되면 **에러**(외부 코드 흡수 차단),
  노드 git 미초기화면 경고(자동 생성 안내).
- 플랫폼 repo 는 `/projects/*` 를 무시하므로 노드의 중첩 `.git` 은 플랫폼 이력과 완전 분리된다
  (submodule 아님, 플랫폼 log 오염 없음).

## Consequences

- 프로젝트별 운영 이력이 노드 단위로 독립 관리된다(유저의 본래 목표). 원하면 노드를 자체 origin
  (예: `<name>-node`)으로 push 할 수 있다.
- `repo/` 와 노드 메타의 두 이력이 깔끔히 분리된다: 코드는 코드 repo, 운영 데이터는 노드 git.
- 정직한 한계: 노드 git 은 플랫폼 pre-commit 훅의 대상이 아니다(노드는 플랫폼 커밋에 안 들어옴).
  강제는 `validate_node`(harness verify/수동 실행)와 자동 커밋 배선으로 달성한다.
- 자동 커밋은 변경이 있을 때만 일어나고(`diff --cached --quiet`), vector 바이너리는 제외해
  이력이 비대해지지 않는다.
