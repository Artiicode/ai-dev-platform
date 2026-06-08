# Changelog
형식: [Keep a Changelog](https://keepachangelog.com) · 버전: SemVer.
플랫폼 변경은 여기, "왜"는 docs/adr/.

## [0.7.0] - 2026-06-08
### Added
- **강제성 ① 보편층(모델·하네스 비종속):** `tools/gen_agent_rules.py` (+ `harness gen-rules`) —
  `platform/prompts/global-system.md`에서 `CLAUDE.md`/`AGENTS.md`/`GEMINI.md`/`.cursorrules`/
  `.github/copilot-instructions.md` 생성(루트+노드). `tools/validate_node.py` (+ `harness validate`) —
  스키마(jsonschema)·구조·시크릿·repo청결·ONBOARDING 검증. `tools/hooks/pre-commit` +
  `tools/install_hooks.py` (+ `harness install-hooks`), `.github/workflows/validate.yml` (CI).
- **강제성 ② MCP 쓰기 게이트웨이:** `mcp/server.py`에 `begin_session`(규칙+토큰) + 토큰 게이트
  쓰기 도구(`append_worklog`/`record_decision`/`ingest_data`/`request_approval`). 시크릿/이력 강제.
- **강제성 ③ 모델 무관 실행층:** `tools/lib/llm.py` (LiteLLM 기반, `harness models`). 키 부재 시 역할
  비활성(임의 폴백 없음). `models.yaml`에 openai/gemini/ollama 예시. `requirements.txt`에 litellm(선택).
- **repo 링크 `symlink` 타입:** `--link-type symlink --target <dir>` — 로컬 기존 프로젝트를 복제 없이
  `repo/`로 심링크. 빈 repo 자동 대체·멱등·대상 미존재 거부. (install.py/init_project.py/CLI/스키마/문서)
### Fixed
- `project_A-node/code/verify.yaml` 누락 보정. 문서 버전 드리프트(ARCHITECTURE/USAGE/curriculum→0.6.0).
  빈 `scenario/debug/` 잔재 제거. 스키마 런타임 미검증(B2) → validate_node 에서 jsonschema 적용.
### Verified
- symlink e2e(멱등/재생성/미존재 에러/빈repo 대체), gen-rules 생성, validate OK, MCP 쓰기 토큰 게이팅+
  시크릿 차단, `harness models` 가용성 판정, project_A 인제스트(html→vector/docx→md/json→sql/png→OCR).
- dev/general 양쪽 소스 동일(diff 무차이). 감사: docs/audit/2026-06-08-*.

## [0.6.0] - 2026-06-08
### Added
- `tools/rebuild.py` + `harness rebuild`: info/ 를 archives/ 에서 완전 재생성(파생물 재현성).
- `tools/verify.py` + `harness verify` (+ /verify): code/verify.yaml 기반 검증 루프, state/verify-report.md.
- `adapters/web-gui/server.py` + index.html + `harness webgui`: stdlib HTTP 백엔드 스켈레톤(동일 MCP 기판 재사용, RAG chat).
- 템플릿 `code/verify.yaml`. ADR 0007.
### Verified
- rebuild 재생성, verify 통과/필수실패(exit≠0), webgui 4개 API, 실제 SentenceTransformer 백엔드 경로 + hash 폴백.

## [0.5.0] - 2026-06-08
### Added
- 동시성 락 `tools/lib/locks.py` (state/lock.json, stale 자동 회수) + `harness lock/unlock`.
- 승인 게이트/감사 `tools/lib/approval.py` (HITL, state/audit.log).
- git worktree 격리 `tools/lib/worktree.py` + `harness worktree`.
- ONBOARDING 자동 생성 `tools/gen_onboarding.py` + `harness onboard` (+ /onboard).
- 디버그 러너 `tools/debug_runner.py` + `harness debug` (+ /debug): dry-run 기본, --execute 시 락+승인 게이트.
- ADR 0006, USAGE 운영 도구 섹션.
### Notes
- 검증: 락 상호배제/해제/stale, worktree 실제 git 브랜치 생성, 승인 auto-approve+감사,
  onboarding 생성(활성티켓/ADR/미해결 파싱), debug dry-run 전체 흐름 PASS.

## [0.4.0] - 2026-06-08
### Added
- 통합 CLI `harness` (init/bootstrap/ingest/serve/info/search/query) + 루트 런처(venv 자동).
- Linux/WSL 셋업: `scripts/setup.sh`, `Makefile`, `.env.example`, `scripts/smoke_test.sh`.
- MCP 서버 트랜스포트 선택(stdio|sse|streamable-http) — 웹 GUI 대비. `adapters/web-gui` 플레이스홀더.
- 사용법 문서 `docs/USAGE.md` (WSL 기준: 설치/인제스트/MCP 등록(Claude Code·Claude Desktop)/웹 GUI/트러블슈팅).
### Changed
- README 빠른시작을 Linux/WSL 중심으로 재작성. mcp.example.json 이 .venv 파이썬 사용.
### Notes
- 검증: harness init/ingest/info/query/search 스모크 PASS, sse 서버 uvicorn 기동 확인.

## [0.3.0] - 2026-06-08
### Added
- 인제스트 추출기(`tools/lib/extractor.py`): pdf/docx/html/이미지(OCR)→텍스트, 선택 의존성 graceful degrade.
- `tools/init_project.py` + `/init-project` 슬래시 커맨드: _template-node 복제로 새 노드 생성.
- 예시 프로젝트 노드 `projects/project_A-node` (path 링크).
### Changed
- router v0.2.0: 추출 후 텍스트 길이로 md/vector 재결정. requirements 에 추출 의존성 추가.
### Notes
- 검증: pdf(6p)/html→vector, docx/이미지(OCR)→md, json→sql, MCP search/query/provenance 전부 통과.
- 알려진 제약: 일부 가상/네트워크 마운트에서는 sqlite 런타임 쓰기가 막힘 → 인제스트는 로컬 디스크에서 실행. (README 운영 노트)

## [0.2.0] - 2026-06-08
### Added
- MCP 서버(`mcp/server.py`, FastMCP): list_info / search_info / query_sql / read_md / get_provenance.
- 로컬 임베딩(`tools/lib/embedder.py`, 기본 bge-m3, 오프라인 hash 폴백) + sqlite-vec 벡터스토어(`tools/lib/vectorstore.py`).
- router 가 실제 적재 수행: md 복사 / json·csv→SQLite / 텍스트 청크+임베딩→sqlite-vec, 원본 archives 이동.
- requirements.txt, Claude Code MCP 등록 예시(`adapters/claude-code/mcp.example.json`), ADR 0003.

## [0.1.0] - 2026-06-08
### Added
- 초기 아키텍처(`docs/ARCHITECTURE.md`)와 디렉토리 골격.
- 노드 템플릿(`projects/_template-node`): manifest link, scenario/debug, info/index 등.
- 툴 스텁: data-to-info 라우터, bootstrap 인스톨러, provenance 라이브러리.
- 정책: 승인 게이트, 시크릿. 스키마: node-manifest / info-index.
- 기존 학습 커리큘럼을 `docs/learning/`으로 이전.
