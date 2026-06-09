---
title: "ai-autodev-harness — 사용법 (Linux / WSL)"
version: 0.10.1
last_updated: 2026-06-08
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

- **임베딩 모델:** 기본 `bge-m3`는 최초 1회 약 2GB 다운로드(로컬·오프라인 추론). 받기 전이거나
  오프라인이면 `export HARNESS_EMBED_BACKEND=hash`로 결정적 폴백을 쓸 수 있습니다(검색 품질↓, 배관은 동일).
- **OCR:** 이미지 인제스트는 `tesseract` 바이너리 필요. 없으면 이미지 파일만 건너뜁니다.

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
```

> **기존 로컬 프로젝트를 심링크로 연결:** `./harness init my_proj --link-type symlink --target /abs/path/to/my_proj`
> 후 `./harness bootstrap projects/my_proj-node`. 대상 디렉토리가 존재해야 하며, 빈 `repo/`는 자동 대체됩니다.
`<name>`은 `my_proj`처럼 이름만 줘도 `projects/my_proj-node`로 해석됩니다.
`make` 단축: `make setup`, `make init NAME=..`, `make ingest NODE=..`, `make serve NODE=..`, `make test`.

## 3. 새 프로젝트 시작

```bash
./harness init my_proj --link-type git-clone --url git@github.com:org/my_proj.git --ref main
./harness bootstrap my_proj          # repo clone + setup 실행
# 자료 투입(아무 포맷): pdf/docx/html/이미지/json/csv/md/txt
cp ~/specs/*.pdf  ~/data/*.json  projects/my_proj-node/data/update/
./harness ingest my_proj             # 추출→md/sql/vector, 원본은 archives/ 보존
./harness info   my_proj
```

라우팅 규칙: 정형(.json/.csv/.tsv)→SQL, 문서는 추출 후 길면 벡터·짧으면 md, 이미지는 OCR.
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
  티켓 종료/주요 결정 후 실행하면 다음 에이전트가 최신 상태를 즉시 파악.
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
- **이미지가 인제스트 안 됨:** `tesseract` 미설치 → `sudo apt-get install tesseract-ocr`.
- **검증:** `make test` (오프라인 hash 임베더로 전체 파이프라인 스모크).
