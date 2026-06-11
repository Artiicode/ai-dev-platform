# 0014. 외부 MCP 레지스트리 + 자연어 운영 플레이북 (일관된 에이전트 운영)

- status: accepted
- date: 2026-06-11
- related: ADR 0009(하네스 중립 옵트인), ADR 0008(강제성), ADR 0002(substrate+MCP)

## Context

유저는 플랫폼을 명령으로 직접 조작하기보다 **에이전트에게 자연어로 요청**한다("bitbucket MCP 붙여줘",
"이 프로젝트 추가해줘"). 목표는 어떤 AI CLI/IDE를 쓰든 그 에이전트가 **일관된 규칙**으로 업무를
수행·관리하는 것이다. 두 가지 공백이 있었다:

1. 외부 MCP(Jira/Figma/Bitbucket 등)는 각 하네스의 MCP 설정을 손으로 편집해야 했고(관리/이식성 없음),
   토큰 같은 시크릿 처리 규칙도 없었다.
2. "자연어 요청 → 어떤 플랫폼 명령" 매핑이 진입규칙에 없어, 에이전트마다 다르게 처리할 여지가 있었다.

## Decision

**(a) 외부 MCP 옵트인 레지스트리 + 병합 명령, (b) 진입규칙(AGENTS.md)에 자연어 운영 플레이북.**

- `platform/mcp-servers.yaml`(옵트인, harnesses.yaml 패턴): `servers:` 정의 + `enabled:` 목록.
  시크릿은 `env` 값에 `${ENV_VAR}` 참조로만(평문 금지).
- `harnesses.yaml` 항목에 `mcp_config` 경로 추가(claude-code=`.mcp.json`, cursor=`.cursor/mcp.json`).
- `harness mcp <harness> [--node NAME]`(`tools/wire_mcp.py`): substrate(노드) 서버 + enabled 외부 서버를
  그 하네스의 MCP 설정으로 **병합**(기존 항목 보존). 평문 시크릿 의심 시 거부. 생성물은 미추적.
- AGENTS.md **§5 운영 플레이북**: "유저가 이렇게 말하면 → 너는 이 명령으로 한다" 표를 정본 진입규칙에
  인코딩. 모든 하네스가 같은 정본(심링크)을 읽으므로 **에이전트 간 일관성**이 구조적으로 보장된다.
  외부 MCP 부착도 이 표에 포함("bitbucket/jira/figma → mcp-servers.yaml enabled + `harness mcp`").

## Consequences

- 유저가 자연어로 "bitbucket MCP 붙여줘" 하면 에이전트는 플레이북대로 레지스트리를 켜고
  `harness mcp` 를 실행한다 — 임의 수작업이 아니라 관리되는 단일 경로.
- 시크릿은 항상 `${ENV_VAR}` 이름참조 → 평문 토큰이 레지스트리/설정/이력에 남지 않는다.
- 정직한 한계: 자연어→명령 매핑은 진입규칙 **지시**라 모델 준수에 의존한다(하드 강제 아님). 단,
  실제로 중요한 부분(기판 변경=MCP 쓰기 게이트웨이, 커밋=훅)은 게이트/훅이 사후 강제한다.
- 새 외부 MCP 지원 = 코드 수정 없이 `mcp-servers.yaml` 에 블록 추가.
