# 0016. 프로젝트 간 공유 지식 — 공유 노드 + 검색 페더레이션

- status: accepted
- date: 2026-06-15
- related: ADR 0015(노드 메타 git), ADR 0010(라우팅 v2), ADR 0002(substrate+MCP)

## Context

여러 프로젝트가 같은 자료(회사 코딩 컨벤션, HW 데이터시트, 공통 API 레퍼런스, 공통 용어 위키)를
참조한다. 지금까지는 그 자료를 **노드마다 따로 ingest** 해야 했다 → 중복·드리프트·N배 임베딩 비용.
MCP 검색은 `NODE_DIR` 단일 노드 한정이라 공유 코퍼스를 함께 볼 방법이 없었다.

`platform/`(prompts·policies·skills)은 이미 프로젝트 공통 *설정* 레이어지만, 공통 *지식*(검색 가능한
`info/`)을 담는 레이어는 없었다. 워크트리 케이스는 별개다: 워크트리는 `repo/`(코드)만 분기하고 노드의
AI 데이터는 노드 루트에 있어 워크트리 간 자동 공유되므로 복제가 필요 없다.

옵션: (A) 공유 노드 + 검색 페더레이션, (B) 공유 `info/` 심링크 — 벡터스토어가 노드별 바이너리라 결국
N배 임베딩·.gitignore 충돌, (C) 노드별 복사 — 드리프트, (D) 공유 repo/submodule — 운영부담 + 검색 통합
여전히 필요.

## Decision

**공유 데이터를 "또 하나의 노드"로 두고, 검색/읽기만 own+shared 합집합으로 페더레이션한다(A).**

- 공유 노드(예: `projects/_shared-node`)는 일반 노드다. `harness init _shared` 로 만들고 공통 자료를
  **한 번만** ingest — ingest/wiki/vector/provenance + node-git(ADR 0015)을 그대로 재사용한다.
- 프로젝트는 manifest `node.shares: [_shared]`(또는 `harness init --shares _shared`)로 **명시적 opt-in**.
  스키마에 `node.shares` 추가. `tools/lib/shared_nodes.py` 가 이름→형제 노드 디렉토리로 해석.
- MCP 서버 페더레이션: `search_info`/`search_all` 은 자기 + 공유 벡터스토어를 질의해 **거리순 병합**하고
  출처 노드를 태깅(`origin`); `read_md`/`query_sql` 는 공유로 폴백(SQL 은 own+shared 의 db 를 ATTACH,
  basename 충돌 시 스키마명 유니크화); `list_info` 는 공유 코퍼스를 보고. `harness search` 도 같은 서버
  경로라 자동 적용.
- **단방향·읽기전용**: 공유 노드는 프로젝트를 보지 않고, 공유 자료 수정은 `_shared` 노드에서 직접 한다.
- `validate_node` 는 `shares` 대상이 실제 노드로 해석되는지 점검(없으면 경고).

## Consequences

- 공통 자료는 한 곳만 업데이트하면 전 프로젝트에 반영된다(중복 0, N배 임베딩 제거).
- 어떤 프로젝트가 공유 지식에 의존하는지 manifest 로 명확(명시 opt-in > 암묵 전역).
- 임베딩 차원이 노드/공유 간 같아야 한다(`models.yaml` 로 통일). 불일치 스토어는 검색 시 그 노드만
  조용히 건너뛴다(전체 실패 방지).
- 기밀 자료는 공유 노드에 두지 않는다(또는 private 노드로 분리). 공유 노드도 자체 node-git 으로
  버전관리·자체 origin push 가능.
- 한계: 페더레이션은 검색/읽기에 한정. 쓰기(worklog/ADR/ingest)는 각 노드 자기 git 에만 일어난다.
