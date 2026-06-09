# Changelog
형식: [Keep a Changelog](https://keepachangelog.com) · 버전: SemVer.
플랫폼 변경은 여기, "왜"는 docs/adr/.

## [0.12.0] - 2026-06-10
### Added
- **라우팅 v2 Phase 1** (`tools/data-to-info/routing.py`): 의미적 route(sql|rag|wiki) 결정 =
  힌트(파일명 `.sql.`/`.rag.`/`.wiki.`·프론트매터 `route:`) → LLM 분류기(role `classifier`→`coder`, 키 있을 때)
  → 크기/확장자 폴백(키 없어도 동작). `info/index.yaml` 에 `route`/`route_by` 기록(provenance 확장).
- `models.yaml` 에 `classifier` 역할(기본 미설정). ADR 0010(+md→엔티티 위키 Phase 2/3 로드맵).
### Verified
- 힌트가 크기 오버라이드(.rag.tiny→rag, .wiki.→wiki, 프론트매터 route:rag→rag), 키 없을 때 폴백
  (json→sql, 작은 텍스트→wiki), index route/route_by 기록 확인.

## [0.11.0] - 2026-06-09
### Added
- 참조자료 업데이트 커맨드 `platform/commands/update-reference.md` (`/update-reference`): 노드
  `data/update/` 자료를 종류별로 인제스트(숫자/표→SQL, 큰 문서→RAG, 작은 권위문서→md).
- 첫 참조 노드 `projects/example_project-node` (link-type path). 업로드 위치 = 그 노드 `data/update/`.
### Changed
- `harnesses.yaml`: 이 인스턴스에서 `claude-code` 활성 → `.claude/commands`(/update-reference 등)·skills,
  `CLAUDE.md` 로컬 생성(미추적). 워크플로: data/update 에 파일 → "업데이트 해줘" 또는 `/update-reference`.

## [0.10.1] - 2026-06-09
### Removed
- 예제 노드 `projects/project_A-node` 제거(템플릿 `_template-node`만 유지). 문서·MCP 예시의 예제명을
  `my_proj`로 일반화.
### Fixed
- pre-commit 훅: 커밋에서 **삭제된 노드는 검증 생략**(`[ -d ]` 가드) — 노드 제거 시 커밋 거부 방지.

## [0.10.0] - 2026-06-09
### Changed
- **하네스 완전 중립화 + 옵트인 어댑터 레지스트리.** 추적되는 건 중립 정본뿐(AGENTS.md,
  platform/skills|commands/*.md, platform/harnesses.yaml). 하네스 고유 산출물(CLAUDE.md/.cursorrules/
  .claude/.cursor/...)은 `harnesses.yaml`의 `enabled`에 켠 하네스에 한해 **로컬 생성·미추적**.
- `gen_agent_rules`(v0.3)·`sync_skills` 가 레지스트리 구동(하드코딩 제거). `sync_skills`는 스킬+커맨드 배포.
- `models.yaml` 역할 기본 **미설정**(벤더 무전제). `web-gui` relay를 `tools/lib/llm.py`(LiteLLM) 경유로.
- 문서/MCP 서버 문구 하네스 중립화. `mcp/server.py` 규칙 로딩 `AGENTS.md` 기준으로 수정.
### Removed
- `adapters/claude-code/**`(커맨드는 중립 `platform/commands/`로 이전, MCP 예시는 `adapters/mcp.example.json`).
  `.cursor/rules/*.mdc` 생성 제거. `manifest.adapters.enabled` 기본 `[]`.
### Notes
- 아무 하네스도 안 켜면 순수 추상 플랫폼(AGENTS.md만). 새 하네스 = harnesses.yaml 에 블록 추가(코드 무수정).

## [0.9.0] - 2026-06-09
### Changed
- **진입 규칙: 정본 1벌 + 심링크.** `gen_agent_rules`(v0.2)가 이제 **`AGENTS.md` 정본만** 만들고
  `CLAUDE.md`/`GEMINI.md`/`.cursorrules`/`.github/copilot-instructions.md`는 정본으로의 **심볼릭 링크**로
  생성. 심링크는 `.gitignore`(미추적) → 드리프트 원천 차단, **AGENTS.md만 git 추적**. 심링크 미지원
  OS(Windows 등)는 **복제 자동 폴백**. `.cursor/rules/*.mdc`는 제거(Cursor가 AGENTS.md 직접 읽음).
- CI 드리프트 검사 → `AGENTS.md` 하나만. `make ready`/`post_clone.sh`에 심링크 생성 단계 추가.
### Notes
- 다른 파일명이 필요하면 `ln -s AGENTS.md <이름>`. (`ln -s 타겟 링크이름` 순서)

## [0.8.1] - 2026-06-09
### Added
- **클론-후-사용 준비:** `scripts/post_clone.sh` + `make ready` — git clone 후 빠지는 것만 멱등 복구
  (venv+의존성 / git pre-commit 훅 / 벡터 스토어 archives→info 재생성). README "git clone 후 바로 쓰기".
### Verified
- 로컬 file:// 테스트 클론 왕복: 클론 직후 .venv·벡터·훅 부재 → 복구 로직 후 search/validate/훅 동작.

## [0.8.0] - 2026-06-08
### Added
- **Cursor 네이티브 룰(.mdc):** `gen_agent_rules.py`가 `.cursor/rules/workspace.mdc`
  (`alwaysApply: true`, frontmatter 최상단)도 생성(루트+노드). CI 드리프트 검사에 포함.
- **하네스 중립 스킬 레지스트리 + 배포:** 정본 `platform/skills/<slug>.md`(+노드 `skills/`)를
  `tools/sync_skills.py` (+ `harness sync-skills`)가 `.claude/skills/`·`.cursor/skills/`로 배포.
  기본 **복제**(이식성), `--link`는 POSIX 심볼릭 링크 선택. 예시 스킬 `update-info` 포함.
### Notes
- 진입 파일은 계속 생성-복제(드리프트 CI 검사) — 심링크 대신. 스킬도 기본 복제로 stack 의존 최소화.
  (general/chat 차용 검토: 진입 파일은 복제가 정설, 심링크는 스킬 단일원본 용도였음.)

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
