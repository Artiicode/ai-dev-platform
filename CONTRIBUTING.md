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

Co-Authored-By: ...
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
- 요약은 명령형·간결하게. 한국어 OK.
- 플랫폼 변경은 `CHANGELOG.md`(무엇), 설계 결정은 `docs/adr/`(왜)에 기록하고 커밋 본문에서 참조.
- 위험·비자명 변경은 본문에 이유를. `Co-Authored-By` trailer 유지.
- 커밋 전 `harness validate` 통과(노드 변경 시). pre-commit 훅이 자동 검사.

예: `feat: 라우팅 v2 — 의미적 route(sql|rag|wiki)`, `chore: 예제 노드 정리`, `fix: info-index 스키마 enum`.
