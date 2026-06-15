---
title: "ai-autodev-harness — 사용법 (Linux / WSL)"
version: 0.22.0
last_updated: 2026-06-11
status: living
audience: [human, ai-agent]
---

# 사용법 (Linux / WSL 1차 타깃)

> 1차 실행 환경은 **Linux / WSL**입니다. Windows에서는 추후 웹 GUI(동일 MCP 서버 재사용)로
> 접속할 예정입니다(§6). 설계 전반은 `docs/ARCHITECTURE.md` 참고.

## 1. 설치

```bash
# WSL/Linux 셸에서 (리포 루트)
bash scripts/setup.sh        # .venv 생성 + 의존성 설치 + tesseract 안내 + .env 생성
source .venv/bin/activate     # 이후 세션마다
cp -n .env.example .env        # 사용할 모델 키 채우기(models.yaml 참조; 미설정도 동작)
```

`scripts/setup.sh`가 하는 일: WSL 감지 → (apt가 있으면) `tesseract-ocr` 설치 → `.venv` 생성 →
`requirements.txt` 설치 → sqlite-vec / mcp import 검증.

- **임베딩 모델:** 기본 `BAAI/bge-m3`(MIT, hybrid, 다국어·한국어 retrieval 우수, ~2GB).
  대안 `Qwen/Qwen3-Embedding-0.6B`(instruction-tuned, ~1.2GB; `HARNESS_EMBED_MODEL`로 교체). 최초 1회 다운로드. 받기 전이거나
  오프라인이면 `export HARNESS_EMBED_BACKEND=hash`로 결정적 폴백을 쓸 수 있습니다(검색 품질↓, 배관은 동일).
- **이미지 자산(asset):** 이미지는 OCR 텍스트를 뽑되, **원본을 `info/assets/`에 보존**하고 위키 페이지가
  `![](../assets/<name>)`로 참조한다. 시각 확인이 필요하면 에이전트가 그 asset 경로를 **`Read`로 on-demand
  열람**한다(비전 캡셔닝/멀티모달 임베딩 없음 — 오프라인·무비용). **OCR 글자가 없는 도면/사진도 더 이상
  건너뛰지 않는다**(파일명·제목으로 임베딩·검색됨). OCR 텍스트 추출은 `tesseract` 바이너리가 있을 때만 추가된다.

## 2. CLI (`./harness`)

`.venv`가 있으면 `./harness`가 자동으로 그 파이썬을 씁니다.

```bash
./harness init <name> [--link-type path|git-submodule|git-clone|symlink] [--url URL] [--ref REF] [--target DIR]
./harness bootstrap <name|node경로> [--dry-run]   # manifest 기준 repo 링크 + 의존성
./harness ingest    <name> [--dry-run]            # data/update/* -> info/
./harness info      <name>                        # md/sql/vector 요약
./harness search    <name> "<질의>" [-k 5]        # 벡터 RAG 시맨틱 검색
./harness query     <name> "SELECT ..."           # info/db 읽기 전용 SQL
./harness serve     <name> [--transport stdio|sse] # MCP 서버
./harness onboard   <name>                        # ONBOARDING.md 재생성
./harness debug     <name> --ticket T --name N --build P [--run-cmd C] [--execute]
./harness lock|unlock <name> [--ticket T] [--status]
./harness worktree  <name> --ticket T [--branch B] [--dry-run]
./harness rebuild   <name>                        # archives 에서 info/ 완전 재생성
./harness verify    <name>                        # code/verify.yaml 체크 실행
./harness webgui    <name> [--port 8800]          # 브라우저 GUI (RAG/SQL/chat)
# 강제성(어떤 AI 에이전트든 규칙 준수):
./harness gen-rules [--node NAME]                 # 정본 AGENTS.md(+활성 하네스 진입파일 심링크) 생성
./harness validate  [<name>] [--strict]           # 노드 적합성 검증(스키마/구조/시크릿/repo청결)
./harness install-hooks                           # pre-commit 훅 설치(git init 후; CI는 항상)
./harness models                                  # 역할별 모델/키 가용성 점검(LiteLLM, 네트워크 불필요)
./harness sync-skills [--node NAME] [--link]      # platform/skills|commands/* → 활성 하네스 배포(기본 복제)
./harness update                                  # 플랫폼 업데이트(git pull --ff-only + 의존성/훅/규칙 갱신)
./harness use   <claude-code|cursor|gemini|copilot>  # 하네스 동적 주입(진입규칙·스킬 로컬 생성)
./harness mcp   <claude-code|cursor> [--node NAME]   # MCP 와이어링(substrate + 외부 MCP → 하네스 설정 병합)
```

> 인자 없이 `./harness` 만 치면 도움말을 출력합니다. 모든 서브커맨드는 `./harness <cmd> -h` 로 옵션 확인.
> **자연어 운영:** 유저가 에이전트에게 "프로젝트 붙여줘 / cursor 쓸게 / jira MCP 붙여줘 / 인제스트 / 검증"
> 처럼 말하면, 에이전트는 진입규칙 **AGENTS.md §5 운영 플레이북**에 따라 위 명령으로 일관되게 수행합니다.

> **기존 로컬 프로젝트를 심링크로 연결:** `./harness init my_proj --link-type symlink --target /abs/path/to/my_proj`
> 후 `./harness bootstrap projects/my_proj-node`. 대상 디렉토리가 존재해야 하며, 빈 `repo/`는 자동 대체됩니다.
`<name>`은 `my_proj`처럼 이름만 줘도 `projects/my_proj-node`로 해석됩니다.
`make` 단축: `make setup`, `make init NAME=..`, `make ingest NODE=..`, `make serve NODE=..`, `make test`.

## 3. 새 프로젝트 시작

> **제로베이스(맨바닥) 새 프로젝트:** `./harness init my_app` (기본 `--link-type path`) → 코드는
> **`projects/my_app-node/repo/` 안에서만** 작성합니다. **플랫폼 루트나 현재 디렉토리에 코드를 만들지
> 마세요.** 에이전트에게 "새 앱/소프트웨어 만들어줘"라고 하면, 진입규칙(AGENTS.md §5)에 따라 먼저
> `harness init` 으로 노드를 만들고 그 `repo/` 안에서 작업합니다. 그 코드를 독립 git 으로 관리하려면
> `projects/my_app-node/repo/` 안에서 `git init` 하세요(플랫폼 이력과 분리).

```bash
# 제로베이스:
./harness init my_app                # projects/my_app-node/ 생성, repo/ 는 빈 코드 디렉토리
# (이후 코드는 projects/my_app-node/repo/ 안에 작성)

# 기존 원격을 clone 해 시작:
./harness init my_proj --link-type git-clone --url git@github.com:org/my_proj.git --ref main
./harness bootstrap my_proj          # repo clone + setup 실행
# 자료 투입(아무 포맷): pdf/docx/html/이미지/json/csv/md/txt
cp ~/specs/*.pdf  ~/data/*.json  projects/my_proj-node/data/update/
./harness ingest my_proj             # 추출→md/sql/vector, 원본은 archives/ 보존
./harness info   my_proj
```

라우팅 규칙: 정형(.json/.csv/.tsv)→SQL, 문서는 추출 후 길면 벡터·짧으면 md, 이미지는 `info/assets/` 보존 +
위키 카드(`![](../assets/..)`)로 항상 적재(무-OCR도 skip 안 됨).
출처는 `projects/my_proj-node/info/index.yaml`(provenance).

## 4. AI가 데이터를 쓰게 하기 — MCP 서버 등록

MCP 서버는 노드의 `info/`(md·sql·vector)를 `list_info / search_info / query_sql / read_md /
get_provenance` 도구로 노출합니다. 노드마다 `NODE_DIR`로 하나씩 띄웁니다.

### (a) MCP 클라이언트 — 예: Claude Code (WSL 안에서 실행)
리포 루트에 `.mcp.json` (예시: `adapters/mcp.example.json`):
```json
{
  "mcpServers": {
    "harness-my_proj": {
      "command": ".venv/bin/python",
      "args": ["mcp/server.py"],
      "env": { "NODE_DIR": "projects/my_proj-node", "HARNESS_EMBED_BACKEND": "local" }
    }
  }
}
```

### (b) Claude Desktop (Windows) → WSL 안의 서버 호출
Windows의 Claude Desktop MCP 설정에서 `wsl.exe`로 진입해 실행합니다(환경변수는 `bash -lc`로 주입):
```json
{
  "mcpServers": {
    "harness-my_proj": {
      "command": "wsl.exe",
      "args": ["-d", "Ubuntu", "--", "bash", "-lc",
        "cd ~/ai-harness && NODE_DIR=projects/my_proj-node HARNESS_EMBED_BACKEND=local .venv/bin/python mcp/server.py"]
    }
  }
}
```
`-d Ubuntu`는 배포판 이름, 경로는 본인 WSL 경로로 바꾸세요.

### (c) CLI로 바로 (등록 없이)
```bash
./harness search my_proj "tool center point calibration"
./harness query  my_proj "SELECT label,x,y,z FROM robot_poses"
```

### (d) 외부 MCP 붙이기 (Jira/Figma/Bitbucket 등) — 레지스트리 + `.env`
플랫폼 substrate 서버는 `mcpServers` 의 한 항목일 뿐이고, MCP 클라이언트는 여러 서버를 동시에 씁니다.
외부 MCP는 **옵트인 레지스트리**로 선언하고 `harness mcp` 가 하네스 설정으로 병합합니다.
```bash
# 1) platform/mcp-servers.yaml 에서 사용할 서버를 enabled 에 추가 (정의 없으면 servers: 에 골격 추가)
#    예) enabled: ["jira", "figma"]   (env 값은 ${ENV_VAR} 이름참조만 — 평문 토큰 금지)
# 2) 자격증명은 루트 .env (gitignored, 단일 소스) 에 넣는다 — export 아님, 재부팅에도 유지
#    JIRA_URL=https://your.atlassian.net
#    JIRA_API_TOKEN=...
# 3) 병합: substrate(노드) + enabled 외부 서버 → 하네스 MCP 설정(.mcp.json / .cursor/mcp.json)
./harness mcp claude-code --node my_proj
```
- 외부 서버는 `tools/harness/mcp_launch.py`(env 주입 셈)로 감싸 기동되어 **`.env` 를 자동 주입**받습니다 →
  셸 `export` 불필요, 평문 토큰이 `.mcp.json` 에 기록되지 않음.
- 새 외부 MCP 지원 = 코드 수정 없이 `platform/mcp-servers.yaml` 에 블록 한 개 추가.
- 값에 `#`·공백이 있으면 `.env` 에서 따옴표로 감싸세요. 이미 export 된 변수는 `.env` 가 덮어쓰지 않습니다.

## 5. 디버그/배포 시나리오
`projects/<name>-node/scenario/debug.md`가 진실 원본(빌드→ssh→scp→실행→로그→커밋).
원격 실행·커밋 등 위험 단계는 `platform/policies/approval-gates.md`의 사람 승인 게이트를 통과합니다.
HW 접속 정보는 `hw/<target>.md`(시크릿은 이름 참조만; 값은 ssh-agent/vault/`.env`).

## 6. 웹 GUI (예정)
Windows에서 브라우저로 대화하는 GUI는 **동일 MCP 서버를 재사용**합니다(새 데이터 계층 없음):
```bash
./harness serve my_proj --transport sse     # http://127.0.0.1:8000 (uvicorn)
```
계획: 얇은 HTTP 레이어가 채팅 UI ↔ 모델(`platform/models/models.yaml`) ↔ MCP 도구를 중계.
또는 `./harness webgui <name> --port 8800` (stdlib HTTP 스켈레톤: /api/info·search·query·chat).
상세는 `adapters/web-gui/README.md`.

## 7. 운영 도구 (락 · 온보딩 · 디버그)
- **동시성 락:** 여러 에이전트가 같은 노드를 만질 때 `harness lock <name> --ticket T` 로 advisory 락.
  `state/lock.json`에 기록되며, 프로세스 사망/TTL 초과 시 자동 회수. 해제는 `harness unlock`.
- **작업 격리:** `harness worktree <name> --ticket T` 로 repo 의 git worktree(독립 작업트리/브랜치) 생성.
- **온보딩 자동화:** `harness onboard <name>` — worklog/adr/info/manifest 를 스캔해 ONBOARDING.md 재생성.
- **이력 자동 인계(수동 onboard 불필요):** `history/ONBOARDING.md`(큐레이션 인계서)가 이력이 바뀔 때마다
  자동 재생성됩니다 — MCP `append_worklog`/`record_decision`/`ingest_data`, `harness verify`. 브리프는
  worklog·ADR뿐 아니라 **노드 `repo/` 의 실제 git 커밋**(이슈/디버깅/기능)과 **verify 테스트 결과**까지
  자동 수집합니다. MCP `begin_session` 이 이 브리프를 `onboarding` 필드로 반환하므로, **새 에이전트는
  핸드셰이크만으로 이전 이력을 인계받습니다.** (작업 경과·결정은 반드시 worklog/ADR에 남길 것 — 안 남기면
  다음 에이전트가 못 봄.)
- **동시 ingest 안전:** 같은 노드에 ingest 가 동시에 돌면 race(원본이 archives로 옮겨지는 사이 충돌)가
  나므로, ingest 는 노드 단위 락(`state/ingest.json`)으로 직렬화됩니다. 두 번째 동시 실행은 거부(rc=2,
  inbox 무손상)되고, 죽은 프로세스의 락은 자동 회수됩니다.
- **디버그/배포:** `harness debug <name> --ticket T --name N --build PATH [--run-cmd C]`.
  기본 dry-run(명령만 출력). `--execute` 시 노드 락 + 위험 단계별 승인 게이트(원격 전송/실행/커밋).
  비대화 자동화는 `HARNESS_AUTO_APPROVE=1` 로 명시 승인. 모든 승인은 `state/audit.log` 에 감사 기록.
  HW 접속 정보는 `hw/<target>.md`(시크릿은 이름 참조만).
- **재생성:** `harness rebuild <name>` — info/ 를 비우고 archives/(진실 원본)에서 완전 재구축(스키마 변경 시 유용).
- **검증 루프:** `harness verify <name>` — `code/verify.yaml` 의 lint/types/unit/scenario 체크 실행, 필수 실패 시 비정상 종료. 리포트는 `state/verify-report.md`.

## 8. 트러블슈팅
- **`disk I/O error` (sqlite):** 가상/네트워크 마운트(예: Windows 드라이브를 `/mnt/c`로 마운트)에서
  발생할 수 있습니다. 노드를 WSL **네이티브 파일시스템**(예: `~/ai-harness`)에 두세요. `/mnt/c/...`는 피함.
- **bge-m3 다운로드 지연/실패:** 임시로 `HARNESS_EMBED_BACKEND=hash`. 캐시는 `~/.cache/huggingface`.
- **이미지 OCR 텍스트가 안 뽑힘:** `tesseract` 미설치 → `sudo apt-get install tesseract-ocr`. (이미지 자체는
  미설치여도 `info/assets/`에 보존되고 위키 카드로 적재됨 — OCR 텍스트만 빠짐.)
- **검증:** `make test` (오프라인 hash 임베더로 전체 파이프라인 스모크).

## 9. 받아서 쓰기 · 자동 준비 · 업데이트 (소비자 워크플로)
이 플랫폼은 **템플릿**입니다 — 유저는 clone 후 자기 노드를 만들어 씁니다. 유저가 만든 노드
(`projects/<name>-node/`)는 git **미추적**(`.gitignore`)이라, clone 본이 upstream과 동일하게 유지되어
업데이트가 충돌 없는 fast-forward 가 됩니다.

```bash
git clone <remote> ai-dev-platform && cd ai-dev-platform
make ready                  # 1회 준비 (또는 ./harness 첫 실행 시 자동) — venv/훅/진입규칙/벡터
source .venv/bin/activate
# … 노드 생성·작업 …
./harness update            # 플랫폼 업데이트: ff 가능하면 fast-forward, 분기 시 머지 + 의존성/훅/규칙 갱신
```
- **업데이트 충돌:** 로컬 이력이 분기됐고 머지 중 충돌이 나면, `update` 가 멈추지 않고 **충돌 파일을
  정확히 출력(`CONFLICT: <file>`, rc=3)** 합니다. 상류 패치는 머지로 반영되며, 충돌 hunk 만 마커가 남습니다.
  AI 에이전트는 진입규칙(§5)에 따라 마커를 직접 해결 → `git add`/`commit` → `verify` 후 **무엇이 자동
  해결됐고 무엇이 사람 확인 필요한지 보고**합니다. 되돌리려면 `git merge --abort`. (커밋 안 된 로컬 변경이
  있으면 머지 전에 거부하니 먼저 커밋/스태시하세요.)
- **상류 이력 재작성(force-push):** 업스트림이 force-push 로 이력을 재작성하면 로컬과 **공통 조상이 없어**
  머지가 불가합니다. `update` 가 이를 감지해 안내(rc=3)하고, `./harness update --resync` 로 **HEAD 를
  `backup-before-resync` 브랜치에 백업한 뒤 `origin` 으로 hard reset** 합니다(노드/데이터는 미추적이라 안전;
  로컬 플랫폼 커밋은 백업 브랜치에 보존). 일회성 이벤트이며 일반 업데이트에는 영향이 없습니다.
- **자동 1회 준비:** clone 본은 venv/git훅/진입규칙 심링크/벡터가 비어 있습니다. `./harness <명령>` 첫
  실행 시 `scripts/ensure_ready.sh` 가 자동으로 1회 준비하고 `.harness-ready`(머신-로컬 표식)를 남깁니다
  (있으면 건너뜀). MCP 서버 기동·`git pull`(post-merge 훅) 시에도 진입규칙·훅을 self-heal 합니다.
  `HARNESS_SKIP_READY=1` 로 우회. **셸 한 번도 없이 claude/cursor만 연 완전 신선 클론**은 venv가 없어
  자동화가 불가하니, 그 경우만 `make ready` 를 1회 수동 실행하세요(AGENTS.md §0 가드 지침).
- 노드를 버전관리하려면: 노드 `repo/`(실제 코드)는 그 자체 git, AI 데이터는 **별도 repo** 권장(플랫폼
  이력과 안 섞기). 깨끗한 새 시작은 GitHub **"Use this template"**.

## 11. 번들 도구 + 작업 세션 (toolkit · harness start)
- **번들 도구(toolkit):** 버전관리되는 플랫폼 도구는 `toolkit/<tool>-node/` 에 둡니다(유저 프로젝트 노드와
  달리 추적됨, 하드 복사). 실행: `./harness tool <name> -- <args>`.
  예: `./harness tool ai-usage-monitor -- --watch 5` (Cursor/Claude Code 사용량·비용 대시보드).
- **작업 세션:** `./harness start [세션이름]` — 처음엔 **화살표 메뉴(↑/↓·숫자·Enter)**로 ① 기본
  하네스(claude-code/cursor), ② claude 실행 방식(`--dangerously-skip-permissions` 여부)을 고르고
  `.harness-local.json`(머신-로컬, 미추적)에 저장합니다. 선택한 하네스의 진입규칙을 주입(`harness use`)한
  뒤 **tmux 세션**(window 이름 `dev`)을 띄웁니다. claude 는 **clone한 플랫폼 디렉토리**에서 실행됩니다:
  세션은 두 윈도우입니다 — `dev`(작업)와 `subtask`(오늘 플랜):
  ```
  [dev]                                  [subtask]
  ┌─────────────┬──────────────────────┐ ┌──────────────────────┐
  │             │ 우상: tmux 치트시트 +  │ │  오늘 할 일 (watch)    │
  │  좌: claude  ├──────────────────────┤ │  - [ ] 오후 2시 Qt …  │
  │             │ 우하: usage --watch    │ │  (60초마다 갱신)       │
  └─────────────┴──────────────────────┘ └──────────────────────┘
  ```
  claude 는 **`./harness` 를 실행한 디렉토리**에서 뜹니다(`--cwd` 로 변경). 옵션: `--harness`,
  `--skip-perms`/`--no-skip-perms`, `--cwd`, `--no-tmux`, `--no-attach`. 예: `./harness start els2.0 --skip-perms`.
  > tmux 필요(`sudo apt-get install tmux`). 이미 tmux 안이면 중첩될 수 있으니 평범한 터미널에서 실행 권장.
- **일 단위 스탠드업 / 할 일:** `./harness standup [node]` — 일일 로그(`<날짜>.md`, 모두 리스트).
  할 일 `--add-task "오후 2시 Qt 세미나"`(또는 `/add-task`), 진행 `--add "..."`, 요약 `--today/--tomorrow`,
  보기 `--show`, 목록 `--list`. **노드 생략 = 플랫폼 개인 플랜**(`<루트>/standup/`, subtask 창에 표시);
  `<node>` 지정 = 프로젝트 standup(`history/standup/`, ONBOARDING 에 요약). 오늘 파일이 없으면 **전날
  미완료(`- [ ]`)·내일계획을 오늘로 carry-over**(없으면 "없음").

## 10. 하네스 주입 (harness use) — 어떤 AI CLI/IDE든
핵심 플랫폼은 하네스 중립이고, 쓸 하네스만 옵트인합니다(`platform/harnesses.yaml`). 진입규칙·스킬은
정본(`AGENTS.md` 등) 1벌만 추적하고, 활성 하네스의 파일은 그 정본으로의 심링크로 로컬 생성(미추적)됩니다.
```bash
./harness use cursor        # enabled 에 cursor 추가 + .cursorrules(→AGENTS.md) + 스킬 로컬 생성
./harness use gemini        # GEMINI.md, ./harness use copilot → .github/copilot-instructions.md
```
유저가 에이전트에게 "cursor 쓸게" 라고 하면 에이전트가 이 명령을 실행하면 됩니다(AGENTS.md §5 플레이북).
MCP까지 필요하면 §4(d) 의 `./harness mcp <harness>`.
