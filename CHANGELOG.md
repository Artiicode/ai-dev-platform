# Changelog
형식: [Keep a Changelog](https://keepachangelog.com) · 버전: SemVer.
플랫폼 변경은 여기, "왜"는 docs/adr/.

## [0.35.0] - 2026-06-16
### Added
- **Excel 시트별 하이브리드 라우팅(정확도↑, 소실 0).** 표(tabular) 시트는 **`info/db/<파일>.sqlite`
  테이블**로 적재(값 타입 보존 → 정확 조회·집계 `query_sql`), 서술 시트는 텍스트로, 그리고 컬럼명·
  미리보기·`query_sql` 포인터를 담은 **위키 카드**(의미검색 발견용)를 함께 생성. `search_all` 의 하이브리드
  (벡터 recall + SQL 정확값)와 맞물린다 — 의미검색으로 표를 찾고 `query_sql` 로 정확값을 뽑는 흐름.
  헤더행+다열 데이터 휴리스틱으로 표/서술 자동 분기, 비표 시트는 텍스트 폴백. `extractor.xlsx_sheets()` +
  router `_ingest_xlsx_tables`/`_xlsx_card`. 다중시트 워크북으로 SQL 정확조회·숫자 집계·발견·서술시트 검증.

## [0.34.1] - 2026-06-16
### Fixed
- **Excel(.xlsx/.xlsm) 인제스트 — 셀 값 소실 버그.** read-only 워크북에서 셀 **객체**를 문자열화하면
  `<ReadOnlyCell '...'.A4>` 플레이스홀더가 박혀 실제 값이 전부 사라졌다. `extractor._xlsx()` 를 추가하고
  `ws.iter_rows(values_only=True)` + `data_only=True` 로 **셀 값**을 직접 추출(시트별 표). `.xlsx/.xlsm` 를
  `SUPPORTED` 에 등록, `openpyxl` 의존성 추가. 임시 워크북으로 추출·ingest·검색까지 실제 값 보존 검증.
  (기존에 잘못 적재된 노드는 `harness update` 후 `harness rebuild <node>` 로 archives/ 에서 재추출.)

## [0.34.0] - 2026-06-16
### Added
- **개인 일일 플랜이 오늘 프로젝트 작업을 자동 집계(roll-up).** 그동안 플랫폼 개인 일일 플랜
  (`<ROOT>/standup`)과 프로젝트 작업 이력(노드 `history/worklog`·`history/standup`)이 별개 파일이라,
  에이전트가 프로젝트에서 남긴 진행이 일일 플랜에 안 보이고 사용자의 `add-task` 만 보였다. 이제
  `harness standup`(노드 생략=개인 플랜) 출력에 모든 `projects/*-node` 의 **오늘 worklog/standup 진행을
  `## [프로젝트 진행]` 섹션으로 집계**(읽기 전용·소급, 노드별 그룹·시각 태그). `standup.project_rollup()`
  추가. 에이전트는 `append_worklog`/노드 standup 만 남기면 일일 플랜에 자동 반영(플랫폼 플랜에 따로 쓸 필요 없음).

## [0.33.2] - 2026-06-15
### Changed
- **환경/머신 의존 절대경로를 추적 파일에서 제거** — `README.md`(symlink 예시 `--target`), toolkit manifest
  `origin`, `session.py` 주석, CHANGELOG 의 사용자 홈 절대경로·머신 고유 env 스크립트 언급을 일반 placeholder
  (`/abs/path/to/...`, 상대표기, `.bashrc/.zshrc`)로 치환. 공개 템플릿 repo 에 특정 PC/사용자 의존 데이터가
  새지 않도록 한다(원칙: 절대경로/머신 고유 값은 커밋 금지 — 예시는 placeholder, 실값은 `.env`/로컬 미추적).

## [0.33.1] - 2026-06-15
### Fixed
- **`harness start` 좌측 claude pane 이 invocation dir 에서 실행**되도록 수정. tmux `-c workdir` 는 시작
  디렉토리만 정하는데, 인터랙티브 셸 rc(`.bashrc`/`.zshrc` 또는 source 되는 env 스크립트)가 그 뒤 cd
  해버려 claude 가 홈 등 엉뚱한 경로에서 떴다. send-keys 로 `cd <workdir> &&` 를 prepend 해 rc 이후에 각
  pane 을 invocation dir 로 고정(좌=claude 포함 dev 윈도우 전 pane).
- **CI(validate-nodes) green 복구** — "AGENTS.md 정본 최신화 확인" 스텝이 최근 푸시들에서 실패했다.
  원인은 AGENTS.md 가 `gen_agent_rules` 생성물인데 기능 추가분이 AGENTS.md 에 직접 편집돼 생성기와
  어긋난 것(0.33.0 에서 정본 이관으로 해소). 재생성 결과가 커밋본과 일치함을 로컬에서 확인.

## [0.33.0] - 2026-06-15
### Added
- **위키 스택 advisor** — `harness wiki <node> --advise`(MCP `wiki_graph` op=advise). 페이지 수·링크밀도·
  type 다양성·고아비율 신호로 "벡터+facet 현행 유지 / GraphRAG·그래프DB·온톨로지 고려"를 **권고만** 한다
  (자동 전환 안 함, 채택은 사람 결정). 임계 도달 시 `--export` 의 (nodes,edges)를 kuzu/GraphRAG 어댑터에
  태우는 on-ramp(ADR 0017). `tools/lib/wiki_graph.py` 에 `advise()` 휴리스틱 임계 추가.
### Changed
- **노드 `code/` → `conventions/` 리네임**(+ `coding_convention/` → `coding/`). `code/` 가 코드가 아니라
  "코드에 대한 규칙(컨벤션/lint/static)"을 담아 `repo/` 와 혼동되던 문제 해소. 템플릿 디렉토리, `validate_node`
  (REQUIRED_DIRS·REPO_FORBIDDEN), `verify.py`, `gen_onboarding`, `global-system.md`, 생성기, 문서 전부 갱신.
  (`archives` 는 역할상 적절해 유지 — `ssot` 는 분산된 SSOT 를 과대주장하므로 미채택.)
### Fixed
- **AGENTS.md 정본 드리프트** — AGENTS.md 는 `gen_agent_rules._platform_body()` 에서 자동 생성되는데,
  최근 기능(이미지 asset·노드 git·공유 노드·위키 v2)의 플레이북/규칙이 AGENTS.md 에 **직접 편집**돼 있어
  `gen-rules` 재생성 시 소실될 상태였다. 해당 내용을 생성기 정본으로 이관해 재생성에도 보존되도록 수정.

## [0.32.0] - 2026-06-15
### Added
- **위키 v2 — 분류(type) facet + `[[링크]]` 그래프 + 외부 항목 import(ADR 0017).** 평면 위키에 다음을 추가:
  (1) **type facet**(hardware/requirements/risk/regulatory/test/ticket/pr/image/general) — ingest 자동추론
  + `wiki_upsert(type=)`, `INDEX.md` 가 type별 그룹(사람용 문서맵), 큐레이션 `SSOT.md` 보존, 검색 `--type`
  필터; (2) **그래프 질의** `tools/lib/wiki_graph.py`(neighbors/backlinks/orphans/path/export, neo4j 불요) —
  `harness wiki --graph|--neighbors|--path|--orphans|--export` + MCP `wiki_graph`; (3) **외부 항목 import**
  `tools/data-to-info/import_items.py` — JSON/TSV(티켓/PR) → key/status/url 위키 페이지(소스 비종속) +
  `harness import`. 임시 노드로 type 추론·그룹 INDEX·그래프 path/neighbors·검색 facet·티켓 import 검증.

## [0.31.0] - 2026-06-15
### Added
- **프로젝트 간 공유 지식 — 공유 노드 + 검색 페더레이션(ADR 0016).** 공통 자료(컨벤션·레퍼런스·HW
  데이터시트)를 매 노드에 복제하던 것을, 전용 **공유 노드**(예: `harness init _shared`)에 한 번만 ingest
  하고 프로젝트가 manifest `node.shares: [_shared]`(또는 `init --shares _shared`)로 opt-in 하도록 변경.
  MCP `search_info`/`search_all`/`read_md`/`query_sql`/`list_info` 와 `harness search` 가 **자기 `info/`
  + 공유 노드 `info/`** 를 합쳐 질의(거리순 병합, 출처 노드 태깅). 단방향·읽기전용. `tools/lib/shared_nodes.py`
  추가, manifest 스키마에 `node.shares`, `validate_node` 가 미해석 shares 경고. 임시 노드로 페더레이션
  방향성(own↔shared)·validate·list_info 검증.

## [0.30.0] - 2026-06-15
### Added
- **노드 메타 자체 git — 에이전트 자동·강제 관리(ADR 0015).** `projects/<name>-node/`가 자기 자신의
  `.git`을 갖고 AI 운영 데이터(context/scenario/history/info/manifest)의 이력을 **노드 단위로** 남긴다.
  플랫폼 repo 는 `/projects/*`를 무시하므로 플랫폼 이력과 **완전 분리**(submodule 아님). `tools/node/node_git.py`
  추가(`ensure_repo`/`commit`/`repo_tracked`). `harness init`/`bootstrap` 이 노드 git 자동 생성,
  `ingest`/`onboard`/`verify` + MCP 쓰기(worklog/ADR/wiki/standup/ingest)가 **자동 커밋**, 직접 편집분은
  새 명령 `harness save <node> -m "..."`. **`repo/`(프로젝트 코드)는 외부 객체** — 노드 git 이 `/repo`를
  추적하지 않으며, `validate_node.py`가 repo/ 추적 시 에러·노드 git 미초기화 시 경고로 강제. 임시 노드로
  end-to-end 검증(init 자동 git, repo/ 미추적, ingest/save 커밋, 불변식 위반 검출).

## [0.29.0] - 2026-06-15
### Added
- **이미지 자산(asset) 관리 — Karpathy "LLM Wiki" 방식.** 이미지 인제스트가 OCR 텍스트만 뽑고 원본을
  버리던(무-OCR 도면/사진은 skip) 손실을 해소. 이제 이미지는 ① 원본을 `info/assets/`에 보존 → ② 위키
  페이지가 `![](../assets/<name>)`로 참조 → ③ 에이전트가 필요할 때 그 경로를 `Read`(멀티모달)로 **on-demand
  열람**(비전 캡셔닝/멀티모달 임베딩 없음 — 오프라인·무비용). **무-OCR 이미지도 더 이상 skip되지 않고**
  파일명·제목으로 임베딩·검색된다. 변경은 `tools/data-to-info/router.py`(`_image_card` 헬퍼 + 이미지 분기)에
  국한, 기존 wiki 흐름(`upsert`→`embed_page`→`reindex`→`provenance.record`→archive) 재사용. 신규 노드는
  `info/assets/`(`.gitkeep`) 기본 포함. 임시 노드로 end-to-end 검증(글자 있는/없는 PNG, 검색, `Read`, 회귀).

## [0.28.1] - 2026-06-15
### Changed
- `harness start` subtask 윈도우 일일 플랜 갱신 주기 10초 → **60초**.

## [0.28.0] - 2026-06-15
### Added
- **스탠드업에 [오늘 할 일] + carry-over** — 오늘 파일이 없으면 전날의 미완료(`- [ ]`)·[요약] '내일'을
  오늘 할 일로 자동 이월(없으면 "없음"). `/add-task "오후 2시 Qt 세미나"`(= `harness standup --add-task`)
  로 추가. **노드 생략 = 플랫폼 개인 일일 플랜**(`<루트>/standup/`, 미추적), `<node>` 지정 = 프로젝트 standup.
- **`harness start` 두 번째 윈도우 `subtask`** — 오늘 플랜을 `watch` 로 표시(10초 갱신; `/add-task` 즉시 반영).
  `platform/commands/add-task.md` 추가(하네스 슬래시 커맨드로 투영).
### Changed
- **`harness start` 좌측 claude 가 `./harness` 실행 디렉토리에서 실행**(기존: 강제 플랫폼 루트). `--cwd` 로 변경.

## [0.27.2] - 2026-06-12
### Added
- **`harness update` 상류 이력 재작성 감지/재동기화** — 업스트림 force-push 로 공통 조상이 사라지면
  머지가 불가하므로, `update` 가 이를 감지해 안내(rc=3)하고 `--resync` 시 HEAD 를
  `backup-before-resync` 브랜치로 백업한 뒤 `origin` 으로 hard reset(노드/데이터 미추적이라 안전,
  로컬 플랫폼 커밋은 백업 보존). 임시 repo 로 감지·복구 시퀀스 검증.

## [0.27.1] - 2026-06-12
### Changed
- **`harness start` 작업 디렉토리 선택 제거** — claude 는 **clone 한 플랫폼 디렉토리(루트)** 에서 실행(기본).
  `--cwd` 로만 변경. `.harness-local.json` 의 `claude_cwd` 불필요.
- **tmux 치트시트 재디자인**(CLI 디자이너 에이전트) — 고정폭 ASCII 단축키를 앞에, 한글(double-width)
  설명을 뒤에 둬 어떤 pane 너비에서도 정렬 유지. 은은한 ANSI 색.
- **tmux 기본 window 이름 = `dev`**.

## [0.27.0] - 2026-06-12
### Added
- **일 단위 스탠드업 로그** — `history/standup/<날짜>.md`(템플릿 노드에 폴더 포함). `harness standup <node>`
  (`--add`/`--today`/`--tomorrow`/`--show`/`--list`) + MCP `standup_add`/`standup_summary`. 형식은
  `## [진행사항]`(시각 태그 항목) + `## [요약]`(오늘/내일). 오늘 분은 `ONBOARDING.md` 자동 인계서에도 요약.
- **`harness start` 화살표 선택 UI** — 하네스·claude 권한·**claude 실행 디렉토리**를 ↑/↓·숫자·Enter 로
  고르고 `.harness-local.json` 에 기본값 저장(stdlib, 의존성 없음; 비TTY는 번호 입력 폴백).
### Changed
- **`harness start` 우상단 pane** = tmux 치트시트 1회 출력 후 **자유 셸**(git watch 대체). 옵션 `--repo`→`--cwd`.
- **`harness update` 충돌 처리** — ff 불가(분기) 시 머지로 상류 패치를 반영하고, 충돌 시 멈추지 않고
  `CONFLICT: <file>`(rc=3)로 정확히 출력. 에이전트가 진입규칙(§5)대로 마커 해결→커밋→verify 후
  자동/수동 해결 내역을 보고. 더티 트리면 머지 전 거부(로컬 작업 보호). git 시퀀스 임시 repo 로 검증.

## [0.26.1] - 2026-06-12
### Fixed
- **CI(`validate-nodes`) 실패 수정** — 0.26.0 의 `tools/` 재정리 때 `.github/workflows/validate.yml` 의
  경로(`tools/validate_node.py`·`tools/gen_agent_rules.py`)를 갱신하지 못해 워크플로가 깨졌다.
  `tools/node/validate_node.py`·`tools/harness/gen_agent_rules.py` 로 수정(두 CI 단계 로컬 재현 통과).

## [0.26.0] - 2026-06-11
### Changed
- **`tools/` 의미별 재정리(이력 보존 `git mv`).** 루트엔 진입점 `harness_cli.py` 만 남기고:
  - `tools/node/` — 노드 작업(`init_project`·`validate_node`·`gen_onboarding`·`rebuild`·`verify`·`debug_runner`)
  - `tools/harness/` — 플랫폼·하네스 와이어링(`gen_agent_rules`·`sync_skills`·`install_hooks`·`wire_mcp`·`mcp_launch`·`session`)
  - 모듈은 `ROOT` 기준 경로(위치 독립). `harness_cli`·`mcp/server` 가 `tools/node`·`tools/harness` 를
    sys.path 에 추가. 훅(`pre-commit`/`post-merge`)·`post_clone.sh`·생성 본문(AGENTS.md)·명령/스킬 문서의
    경로 참조 일괄 갱신. 전체 회귀 테스트(컴파일·standalone·CLI·MCP self-heal·ingest·훅 문법) 통과.

## [0.25.0] - 2026-06-11
### Added
- **`harness start [세션이름]`** — 작업 세션 런처. 기본 하네스(claude-code/cursor)·claude 실행 플래그
  (`--dangerously-skip-permissions` 여부)를 1회 묻고 `.harness-local.json`(머신-로컬·미추적)에 저장,
  선택 하네스의 진입규칙을 주입(`harness use`)한 뒤 **tmux 세션**을 띄운다: 좌=claude, 우상=git status
  watch(에이전트 파일변경 근사 미러), 우하=ai-usage-monitor `--watch`. 옵션 `--harness/--skip-perms/
  --no-skip-perms/--repo/--no-tmux/--no-attach`. bare `./harness` 는 그대로 help(비대화·CI 안전).
  - 참고: claude/cursor 가 자기 작업을 별도 pane 으로 스트리밍하는 기능이 없어 "에이전트 실시간 미러"는
    불가 — 우상단은 근사치(git 변경 감시).

## [0.24.0] - 2026-06-11
### Added
- **toolkit/ 번들 도구 노드** — 유저 프로젝트 노드(`projects/*`, 미추적)와 달리 `toolkit/<tool>-node/`
  는 **버전관리(추적)**되어 플랫폼과 함께 배포된다. 형태는 projects 호환(`repo/` + `manifest.yaml`).
- **`ai-usage-monitor` 번들** — Cursor/Claude Code 사용량·비용 터미널 대시보드를 `toolkit/` 에 **하드
  복사**(심링크 아님, 런타임 잔여물 제외). CLI(`--watch`)는 `requests` 만 필요(PySide6 GUI 불필요).
- **`harness tool <name> -- <args>`** — toolkit 도구를 플랫폼 venv 로 실행(`python -m <entry.module>`,
  `PYTHONPATH=repo`). 예: `./harness tool ai-usage-monitor -- --watch 5`. AGENTS.md §5 플레이북에 추가.

## [0.23.0] - 2026-06-11
### Fixed
- **제로베이스 새 프로젝트가 노드 안에서 생성되도록.** 에이전트가 "새 소프트웨어 만들어줘" 요청에
  플랫폼 루트/현재 디렉토리에 코드를 쏟던 문제. AGENTS.md §2(파일 배치)·§5(플레이북)·노드 규칙에
  **"새 코드는 `projects/<name>-node/repo/` 안에서만, 루트 금지"**를 명시 + 제로베이스 플레이북 행 추가.
- **템플릿 `repo/` 빈 디렉토리 보존** — `.gitkeep` 추가(빈 디렉토리는 clone 에 안 와서 새 노드에 `repo/`
  가 누락될 수 있었음). `harness init` 도 항상 `repo/` 를 생성하고, 제로베이스용 다음-단계 안내를 출력.
### Docs
- USAGE.md §3 에 제로베이스 새 프로젝트 예시/주의 추가.

## [0.22.0] - 2026-06-11
### Changed
- **외부 MCP 자격증명을 `.env` 단일 소스로** (export 폐기). `harness mcp` 가 외부 서버를
  `tools/mcp_launch.py`(env 주입 exec 셈)로 감싸 기동 → 서버가 루트 `.env`(gitignored)를 자동
  주입받는다. 셸 `export` 불필요·재부팅에도 유지, 평문 토큰을 `.mcp.json` 에 쓰지 않음(env 블록 미기록).
  `.env.example` 에 외부 MCP 키 예시 섹션, AGENTS.md §5 플레이북도 ".env 에 넣게 안내"로 갱신.
  레지스트리(`mcp-servers.yaml`)는 여전히 `${ENV_VAR}` 이름참조만(평문 금지).

## [0.21.1] - 2026-06-11
### Fixed
- **동시 ingest race 차단.** 같은 노드 inbox(`data/update/`)에 대해 두 ingest가 동시에 돌면 한쪽이
  원본을 `archives/`로 옮긴 사이 다른 쪽이 그 파일을 찾다 `FileNotFoundError` 가 났다. 노드 단위
  **ingest 전용 락**(`state/ingest.json`, O_EXCL + PID/TTL stale 자동 회수)으로 동시 실행을 차단
  (두 번째 실행은 rc=2 로 거부, inbox 무손상). 파일 이동은 `FileNotFoundError` 를 흡수해 멱등.
  `locks` 모듈을 이름 있는 락(work `lock.json` 과 분리)으로 일반화. `.gitignore` 에 `state/ingest.json`.

## [0.21.0] - 2026-06-11
### Added
- **외부 MCP 레지스트리**(ADR 0014). `platform/mcp-servers.yaml`(옵트인) — Jira/Figma/Bitbucket 등을
  `servers:`+`enabled:` 로 선언(시크릿은 `${ENV_VAR}` 참조만). `harness mcp <harness> [--node NAME]` 가
  substrate 서버 + enabled 외부 서버를 하네스 MCP 설정(.mcp.json/.cursor/mcp.json)으로 병합(기존 보존,
  평문 시크릿 거부). harnesses.yaml 에 `mcp_config` 경로 추가.
- **운영 플레이북** — AGENTS.md §5: "자연어 요청 → 플랫폼 명령" 매핑표를 정본 진입규칙에 인코딩.
  유저가 "bitbucket MCP 붙여줘"/"프로젝트 추가해줘" 라고 하면 모든 하네스의 에이전트가 동일 경로로
  처리(임의 수작업 금지, 시크릿 이름참조, 기판변경은 게이트/훅).

## [0.20.0] - 2026-06-11
### Added
- **작업 이력 자동 인계**(ADR 0013). 새 에이전트가 이전 작업(이슈·디버깅·결정·테스트)을 자동으로 이어본다.
  - `gen_onboarding` 가 **repo git 커밋 로그** + **verify 테스트 결과**(`state/verify-report.md`)를 브리프에
    자동 수집(수기 worklog 없이도 최소 이력 확보).
  - `ONBOARDING.md` 자동 재생성 트리거: MCP `append_worklog`/`record_decision`/`ingest_data`,
    `harness verify`. 수동 `harness onboard` 불필요.
  - MCP `begin_session` 이 최신 ONBOARDING을 `onboarding` 필드로 **반환** → 핸드셰이크만으로 이력 인계.
  - AGENTS.md §3에 이력 자동 인계 + 로그 작성 의무 명시.

## [0.19.0] - 2026-06-11
### Added
- **`harness use <harness>`** — 하네스 동적 주입. 이름(claude-code|cursor|gemini|copilot)만 받아
  레지스트리 `enabled`에 추가 + 진입규칙 심링크(예: `.cursorrules`) 생성 + 스킬/커맨드 투영을
  멱등 수행. 유저가 "cursor 쓸게" 하면 AI가 이 한 줄로 셋업. AGENTS.md §0에 사용 지침 추가.
### Fixed
- 서브커맨드 없이 `./harness` 만 실행하면 argparse 에러(exit 2) 대신 **도움말 출력 후 정상 종료**.
  (clone 후 첫 `./harness` 가 부트스트랩만 하고 깔끔히 끝나도록.)

## [0.18.0] - 2026-06-11
### Added
- **진입점 무관 1회 자동 부트스트랩**(ADR 0012). 멱등 가드 `scripts/ensure_ready.sh` +
  머신-로컬 스탬프 `.harness-ready`(미추적). 준비되면 즉시 no-op, 아니면 `post_clone.sh`에 위임.
  - **`./harness` 런처**가 모든 명령 전에 호출 → 첫 실행 시 venv/훅/진입규칙/벡터 자동 준비.
  - **MCP 서버 기동**(`mcp/server.py`)이 진입규칙 심링크·git 훅을 self-heal(가벼움; stdio 보호 위해
    stdout→stderr, 실패해도 서버는 계속). venv 생성/모델 다운로드는 안 함.
  - **git `post-merge` 훅**이 `git pull` 후 진입규칙·훅을 갱신.
  - `HARNESS_SKIP_READY=1` 로 전 구간 우회(CI/테스트).
- AGENTS.md §0에 부트스트랩 가드 지침(완전 신선한 clone을 셸 없이 claude/cursor로 바로 연 경우용).
### Changed
- `post_clone.sh`가 성공 시 `.harness-ready` 스탬프를 생성. `.gitignore`에 스탬프 추가.

## [0.17.2] - 2026-06-10
### Added
- **`harness update`** — `git pull --ff-only` 후 의존성/훅/진입규칙을 갱신하는 소비자용 업데이트
  명령. fast-forward 실패(로컬 이력 분기) 시 자동 머지하지 않고 안내만 한다.
- README에 **"플랫폼 업데이트 받기 (소비자)"** 섹션 추가.
### Changed
- **유저 노드/데이터 git 미추적** — `.gitignore`에 `/projects/*`(단 `_template-node` 제외) 추가.
  clone 본이 upstream과 바이트 동일하게 유지되어 `git pull`/`harness update`가 충돌 없는
  fast-forward로 동작한다(템플릿 순수성 원칙: 데이터/프로젝트 specific 내용은 추적하지 않음).
  노드를 버전관리하려면 별도 repo 사용 권장.

## [0.17.1] - 2026-06-10
### Added
- **commit-msg 훅(Conventional Commits 강제)** — `tools/hooks/commit-msg`, `harness install-hooks`가 함께 설치.
  형식 위반 커밋 거부(`<type>: <summary>`). 우회는 `git commit --no-verify`.
- **기밀 노드 정책** — `harness init <name> --private` → manifest `node.private: true` + 노드-로컬
  `.gitignore`(`archives/`·`info/`·`data/update/*` 미추적). `validate_node`가 private 노드 데이터가
  git 추적되면 **커밋 차단**(이중 안전망). 스키마에 `node.private` 추가.
### Changed
- CONTRIBUTING: **커밋 메시지·코드 주석은 영어로**(English) 작성 규칙 명시.

## [0.17.0] - 2026-06-10
### Removed
- 예제 프로젝트 노드 제거 — 템플릿은 `_template-node`(노드 템플릿)만 포함한다. 실제 노드는
  `harness init <name>` 으로 생성(데이터/프로젝트 specific 내용은 템플릿에 싣지 않는 원칙).
- 루트 `.mcp.json`(인스턴스 wiring) 미추적(.gitignore) — 중립 예시는 `adapters/mcp.example.json`.
### Added
- `CONTRIBUTING.md` — 커밋 컨벤션(Conventional Commits) + 템플릿 순수성 원칙.

## [0.16.2] - 2026-06-10
### Changed
- 예제 노드를 `example_project` 로 명명(예제임이 명확하도록).

## [0.16.1] - 2026-06-10
### Added
- `.mcp.json`(루트): Claude Code가 예제 노드의 MCP 서버를 **상주**로 띄우도록 등록.
  모델 로드(18s)는 첫 호출 1회만, 이후 검색 ~80ms·인제스트 로드 0. (CPU 측정상 원격 GPU 불필요)

## [0.16.0] - 2026-06-10
### Changed
- **기본 임베딩 → `BAAI/bge-m3` 로 환원**(0.15.0 의 Qwen 기본 되돌림). 한국어 KorQuAD 실측에서 bge-m3 가
  Qwen3-0.6B 를 전 지표 우세(R@1 0.85 vs 0.75, MRR 0.913 vs 0.853). Qwen3-0.6B 는 대안 유지. ADR 0011 갱신.
  (비대칭 인코딩 `embed_query` 는 Qwen 대안용으로 유지 — bge/hash 엔 무해.)
### Notes
- 교훈: MTEB 리더보드(대형 모델 기준)를 소형 모델·실제 언어로 일반화 말 것 — 실측이 결정을 뒤집음.

## [0.15.0] - 2026-06-10
### Changed
- **기본 임베딩 모델 → `Qwen/Qwen3-Embedding-0.6B`** (대안 `BAAI/bge-m3`). 2026 MTEB 다국어 상위 +
  실문서 비교(영문 대등~우위, 한국어/다국어 우위) + 경량(~1.2GB)·1024차원 드롭인. ADR 0011.
- embedder **비대칭 인코딩**: 문서 plain / 쿼리 `embed_query`(Qwen 류 instruction 자동, bge·hash 무프리픽스).
  `search_info` 가 `embed_query` 사용. `embedder.DEFAULT_MODEL` + env/`models.yaml` 기본값 갱신.
### Verified
- 실문서(영문 코딩표준 PDF) bge-m3 vs Qwen3-0.6B 비교: instruction 적용 시 Qwen 대등~우위. 통합 `harness search`
  가 Qwen+instruction 자동 적용 확인. (기밀 테스트 문서·산출물은 커밋하지 않음)

## [0.14.0] - 2026-06-10
### Added
- **라우팅 v2 Phase 3 — 하이브리드 검색** `search_all(query,k)`: 벡터(위키+RAG, `kind` 태그) + 질의어와
  매칭되는 SQL 테이블/컬럼 힌트(결정적; 정확값은 `query_sql` 후속). `search_info` 에 `kind` 태그,
  `harness search` 표시 갱신(위키/RAG/SQL 구분).
- **옵션: 키 기반 위키 자동 병합** `tools/lib/wiki_compile.py` + `harness wiki-compile`: LLM 역할(키) 있을 때
  위키 페이지 무인 병합/중복제거/[[링크]], 없으면 graceful no-op(에이전트 수동·키 불필요). ADR 0010 완료.
### Verified
- 혼합 자료(sql/rag/wiki) end-to-end: route 분배, search_all 이 위키/RAG hit(kind) + SQL 테이블 힌트 반환,
  wiki-compile 키없음 graceful no-op, validate 통과.

## [0.13.0] - 2026-06-10
### Added
- **라우팅 v2 Phase 2 — 자기유지 엔티티 위키.** `tools/lib/wiki.py`: 엔티티 페이지(`info/wiki/<slug>.md`,
  frontmatter+`[[links]]`)·INDEX·벡터 임베딩(doc_id=`wiki:<slug>`, 검색 일원화)·dangling 리포트·병합용 delete.
  route=wiki 시 router 가 소스별 페이지 1차 적재+임베딩. **개념 분할·병합 '지능'은 구동 에이전트가 담당**
  (키 불필요): MCP `wiki_list/wiki_read/wiki_links/wiki_upsert`(토큰 게이트), `harness wiki [--reindex|--embed|--links]`,
  `/update-reference` 에 병합 단계 추가.
- info-index 스키마 `store` 에 `wiki` 추가.
### Verified
- 소스 2개→부분 페이지 2개+임베딩→에이전트 병합(1 엔티티+`[[Arm]]`)+부분 삭제→검색이 위키 반환,
  dangling 리포트, store=wiki 스키마 검증 통과.

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
