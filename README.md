# ai-autodev-harness

여러 AI 에이전트(모델·하네스 무관)가 협업해 소프트웨어 프로젝트를 개발/테스트/
디버그/배포하는 **모델-무관(model-agnostic) 자동개발 하네스**.

## 핵심 아이디어
- **기판(substrate) + 어댑터.** 지식은 어디서든 읽히는 파일/DB/벡터(진실 원본)로 두고,
  각 AI 플랫폼은 얇은 어댑터로 접근. MCP 서버는 같은 기판을 고충실도로 노출.
- **코드와 AI 메타 분리.** `projects/<name>-node/repo`(실제 코드) vs 그 형제 폴더들(AI 운영 데이터).
- **data → info 파이프라인.** `data/update/`에 무엇이든 넣고 변환 → 특성별 md/SQL/RAG 라우팅,
  원본은 `archives/`, 출처는 `info/index.yaml`.

## 시작점
1. 설계 전체: `docs/ARCHITECTURE.md`
2. 멘탈 모델(학습): `docs/learning/harness-curriculum.md`
3. 새 프로젝트 생성: `_template-node` 복제 → `tools/bootstrap/install.py` (자동 링크/설치)
4. 버전: `VERSION` · 변경 이력: `CHANGELOG.md` · 설계 결정: `docs/adr/`

## 레이아웃
```
platform/   글로벌 AI 설정(프롬프트/정책/모델 매핑)
tools/      data→info 변환기 + 부트스트랩
mcp/        기판을 노출하는 MCP 서버
adapters/   기판 접근 어댑터(MCP·웹GUI). 하네스 활성화는 platform/harnesses.yaml
projects/   <name>-node/ 프로젝트 노드 (+ _template-node 템플릿)
docs/       ARCHITECTURE / adr / schemas / learning
```

## git clone 후 바로 쓰기 (다른 곳/머신)
```bash
git clone <remote-url> ai-dev-platform && cd ai-dev-platform
make ready              # 멱등: venv+의존성 + git훅 + 벡터 재생성(archives→info)
source .venv/bin/activate
# 오프라인이면:  HARNESS_EMBED_BACKEND=hash make ready
```
`.venv`/git훅/진입규칙 심링크(CLAUDE.md 등)/벡터스토어, 그리고 **사용자가 만든 노드(`projects/<name>-node/`)**
는 git에 추적되지 않는다(재생성·로컬 전용). 추적되는 정본은 **코어 + `_template-node` + `AGENTS.md`·스킬·커맨드**뿐.
→ clone 본이 upstream과 동일하게 유지되어 **`git pull`/`harness update`로 충돌 없이 플랫폼 업데이트**를 받는다.
`make ready`가 venv·훅·진입규칙·벡터를 복구한다. **WSL은 네이티브 FS에 클론**(`/mnt/c` 금지).

## 플랫폼 업데이트 받기 (소비자)
이 템플릿을 받아 쓰는 유저는 **노드·데이터를 이 repo에 커밋하지 않는다**(자동 미추적). 그래서 업데이트가 깔끔:
```bash
./harness update     # git pull --ff-only + 의존성/훅/진입규칙 갱신 (필요시 make ready 로 벡터 재생성)
```
- 노드/데이터 미추적 → clone 본은 항상 upstream과 동일 → 업데이트가 fast-forward.
- 노드를 버전관리하려면: 노드의 `repo/`(실제 코드)는 그 자체 git, AI 데이터는 **별도 repo** 권장(플랫폼 이력과 안 섞기).
- 깨끗한 새 시작: GitHub **"Use this template"** 로 새 repo 생성도 가능.

## 빠른 시작 (Linux / WSL)
```bash
bash scripts/setup.sh && source .venv/bin/activate     # 의존성 + tesseract + .env
./harness init my_proj --link-type path                # 새 프로젝트 노드
# 이미 로컬에 있는 프로젝트를 심볼릭 링크로 연결(복제 없이 참조):
./harness init my_proj --link-type symlink --target /abs/path/to/my_proj
./harness bootstrap projects/my_proj-node              # repo/ 심링크 생성
cp ~/data/*  projects/my_proj-node/data/update/        # 아무 포맷 투입
./harness ingest my_proj                               # 추출→md/sql/vector
./harness search my_proj "검색어"                       # 벡터 RAG
./harness serve  my_proj                               # MCP 서버 (MCP 지원 하네스 연결)
```
전체 사용법(설치·인제스트·MCP 등록·웹 GUI·트러블슈팅): **docs/USAGE.md**

## 환경 / 주의
- **1차 타깃: Linux / WSL.** Windows는 추후 웹 GUI(동일 MCP 서버를 `--transport sse`로 재사용)로 접속.
- 노드는 WSL **네이티브 FS**(예: `~/ai-harness`)에 두세요. `/mnt/c/...` 같은 마운트는 sqlite
  `disk I/O error`가 날 수 있습니다.
- 기본 임베딩 `BAAI/bge-m3`(MIT, hybrid, 다국어·한국어 retrieval 우수, 1024차원, ~2GB 최초 1회 다운로드).
  대안 `Qwen/Qwen3-Embedding-0.6B`(`HARNESS_EMBED_MODEL`로 교체). 오프라인/테스트는 `HARNESS_EMBED_BACKEND=hash`.
- 이미지 OCR은 `tesseract` 바이너리 필요.
