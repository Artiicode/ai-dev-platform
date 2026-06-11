# 0012. 진입점 무관 1회 자동 부트스트랩

- status: accepted
- date: 2026-06-11
- related: ADR 0008(강제성 ①②③), ADR 0009(하네스 중립), 0.17.2(유저 노드 미추적)

## Context

clone 본은 의도적으로 비어 있다: `.venv`/의존성, git 훅, 진입규칙 심링크(`CLAUDE.md`/`.cursorrules`),
벡터 스토어가 모두 `.gitignore` 미추적(재생성 가능·대용량·경로종속)이다. 따라서 clone 직후엔 `make ready`
(=`scripts/post_clone.sh`) 1회가 필요하다. 문제는 유저가 **반드시 `./harness`로 들어오지는 않는다**는 점이다:

- `./harness <cmd>` 런처로 진입,
- 폴더에서 claude/cursor를 직접 켜서 진입규칙·MCP로 진입,
- `git pull` 후 진입.

진입점마다 준비 상태가 다르면 "규칙이 안 걸리는" 조용한 실패가 난다. LLM이 프롬프트 지시로 자가
부트스트랩하고 적용 후 프롬프트를 자가편집하는 방식은 (a) 추적 정본 `AGENTS.md`를 수정해 clone 본을
upstream과 분기시켜 0.17.2의 무충돌 pull을 깨고, (b) 전역(공유) 프롬프트로 머신-로컬 상태를 표현할 수
없으며, (c) 비결정적이라 채택하지 않는다.

## Decision

**단일 멱등 가드 `scripts/ensure_ready.sh` 를 만들고, 모든 진입점이 그것을 호출한다. 상태는 머신-로컬
스탬프 `.harness-ready`(미추적)로 판정한다.**

- `ensure_ready.sh`: 스탬프 + venv 존재 시 즉시 no-op. 없으면 `post_clone.sh`(무거운 1회 준비:
  venv·의존성·훅·진입규칙·벡터)에 위임하고, `post_clone.sh`가 성공 시 스탬프를 찍는다.
  `HARNESS_SKIP_READY=1` 로 우회(CI/테스트). 진행 로그는 stderr로 보낸다.
- 진입점별 호출:
  - **① `./harness` 런처** — 모든 명령 전에 `ensure_ready.sh`(무거운 1회 준비 가능).
  - **② MCP 서버 기동**(`mcp/server.py`) — venv 안에서 도는 시점이므로 가벼운 self-heal만:
    진입규칙 심링크·git 훅 재생성. venv 생성/모델 다운로드는 하지 않는다. stdio 프로토콜 보호를
    위해 stdout→stderr 리다이렉트, 실패해도 서버는 계속 뜬다.
  - **③ git `post-merge` 훅** — `git pull`/merge 후 진입규칙·훅을 가볍게 갱신(무거운 작업 없음).
- 남는 빈틈(정직한 한계): **완전 신선한 clone을 셸 명령 없이 claude/cursor로 바로 연 경우** venv가
  없어 자동화가 불가능하다(MCP/`.mcp.json`도 미추적이라 안 뜸). 이 경우는 `AGENTS.md` §0의 가드
  지침("`.harness-ready` 없으면 `make ready` 1회")으로 커버한다 — 프롬프트 자가편집은 하지 않는다.

## Consequences

- 어느 진입점으로 들어와도 "준비됨" 상태로 수렴한다(첫 셸 진입은 자동, 이후는 self-heal).
- 정본 `AGENTS.md`는 그대로 유지되어 0.17.2의 무충돌 업데이트가 보존된다.
- 스탬프가 머신-로컬이라 머신마다 독립적으로 정확히 1회 준비된다.
- 비용: 준비된 클론에서 진입점 호출당 파일 존재 검사 2회(무시 가능). MCP self-heal은 기동당
  심링크/훅 재생성 1회(네트워크 없음).
