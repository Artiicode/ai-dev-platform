# 기여 가이드 (CONTRIBUTING)

`ai-autodev-harness`는 **유저가 받아서 원하는 스택을 추가해 쓰는 템플릿 플랫폼**이다.
아래 두 가지를 지킨다: (1) 템플릿 순수성, (2) 커밋 컨벤션.

## 1. 템플릿 순수성 — 무엇을 커밋하나

**커밋한다 (플랫폼 골격):**
- 환경/의존성 구성: `requirements.txt`, `scripts/`, `Makefile`, `platform/`(정책·모델 매핑·스킬·커맨드·진입규칙 원본).
- 도구/기판: `tools/`, `mcp/`, `adapters/`(중립 어댑터·예시), `docs/`, `.github/`.
- 노드 **템플릿**: `projects/_template-node/` (실제 노드를 만드는 틀).
- 진입 규칙 정본 `AGENTS.md`, 스킬/커맨드 정본(`platform/skills|commands/*`).

**커밋하지 않는다 (데이터/프로젝트·인스턴스 specific):**
- 실제 프로젝트 노드(`projects/<name>-node/`)와 그 안의 데이터 — 유저가 `harness init`으로 생성·관리.
- 인스턴스 wiring: `.mcp.json`(어떤 노드를 MCP로 띄울지), `.env`, venv, 벡터 스토어(재생성 가능).
- 기밀/회사 자료. (기밀 노드는 `archives/`·`info/` 미추적 정책 적용 후 다룰 것)

원칙: **"환경 구성에 필요한 것"은 OK, "데이터·프로젝트 specific"은 금지.** clone 후 `make ready`로 환경 복구,
`harness init <name>`으로 자기 노드 생성.

## 2. 커밋 컨벤션 — Conventional Commits

형식:
```
<type>: <한 줄 요약>

<본문(선택)>
```

| type | 의미 |
|---|---|
| `feat` | 새 기능 |
| `fix` | 버그 수정 |
| `docs` | 문서만 변경 |
| `refactor` | 동작 변화 없는 코드 개선 |
| `perf` | 성능 개선 |
| `test` | 테스트 추가/수정 |
| `build` | 빌드/의존성(requirements 등) |
| `ci` | CI 설정(.github/workflows) |
| `chore` | 그 외 잡무 — src 동작·기능과 무관한 유지보수(이름변경, .gitignore, 버전 범프, 정리) |
| `revert` | 이전 커밋 되돌림 |

규칙:
- **커밋 메시지·코드 주석은 영어로 작성**(commit messages and code comments in English). 산문 문서(README/
  USAGE/ADR 등)는 별도. 요약은 명령형·간결하게.
- **`commit-msg` 훅이 형식을 강제**한다(`harness install-hooks`로 설치). 위반 시 커밋 거부 — 일회 우회는 `git commit --no-verify`.
- 플랫폼 변경은 `CHANGELOG.md`(무엇), 설계 결정은 `docs/adr/`(왜)에 기록하고 커밋 본문에서 참조.
- 위험·비자명 변경은 본문에 이유를.
- **AI 시그니처 트레일러 금지:** 커밋 메시지/PR 본문에 `Co-Authored-By:` /
  `Co-authored-by:` / `Made-with:` / `Generated with …` 등 AI·도구 귀속 문구를
  **넣지 않는다**. Claude Code는 `.claude/settings.json`의
  `includeCoAuthoredBy: false` + `attribution.commit/pr: ""` 로 강제하고,
  Cursor는 Settings → Agents → Attribution 끄기 +
  `~/.cursor/cli-config.json`의 `attribution.attributeCommitsToAgent` /
  `attributePRsToAgent` 를 `false` 로 둔다. Git 훅이 트레일러를 **제거**하고
  남아 있으면 거부한다(`prepare-commit-msg` / `commit-msg` / `post-commit`).
  외부 프로젝트(starfish 등): `python3 tools/harness/install_project_git_hooks.py <repo>`.
- **운영 규칙 정본은 하네스 중립:** Claude/Cursor/Gemini 공통 규칙은
  `platform/prompts/global-system.md`(→ `AGENTS.md`)와 `platform/policies/`에만 둔다.
  Cursor 전용 `.cursor/rules/*.mdc`에만 쓰지 않는다(ADR 0019). `.cursor/`·`CLAUDE.md`
  심링크 등 하네스 투영물은 `.gitignore`(미추적).
- 커밋 전 `harness validate` 통과(노드 변경 시). pre-commit 훅이 자동 검사.

예: `feat: routing v2 — semantic route (sql|rag|wiki)`, `chore: tidy example node`, `fix: info-index store enum`.

## 3. 기밀(private) 노드

기밀/회사 자료를 다루는 노드는 **데이터가 절대 커밋되지 않도록** private 로 만든다:
```
./harness init <name> --private
```
- manifest 에 `node.private: true` + 노드-로컬 `.gitignore`(`archives/`·`info/`·`data/update/*` 미추적) 생성.
- `validate_node`(pre-commit/CI)가 **private 노드의 데이터가 git 추적되면 커밋 거부**(이중 안전망).
- 추적되는 건 빈 스켈레톤(manifest 등)뿐 — 원본·추출물·벡터는 로컬에만 남는다.
