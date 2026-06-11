---
title: 툴 작성 규칙
version: 0.1.0
status: living
---
# tools/ — 툴 작성 규칙

플랫폼 내부 툴(특히 data→info 변환기)이 지켜야 할 규칙.

## 공통 계약
1. **멱등(idempotent).** 같은 입력 재실행 시 중복 생성 금지(해시로 판단).
2. **provenance 필수.** 모든 산출물은 `tools/lib/provenance.py`로 출처(원본 경로/sha256/시각/툴명)를
   `info/index.yaml`에 기록.
3. **원본 보존.** 입력 파일은 변환 후 `archives/`로 이동(삭제 금지).
4. **파생물 격리.** 산출물은 `info/{md|sql|vector}` 아래에만.
5. **드라이런 지원.** `--dry-run`으로 무엇을 할지 출력만.
6. **표준 인터페이스.** stdin/인자 → 표준 종료코드, 로그는 stderr.
7. **의존성 최소.** 무거운 라이브러리는 선택적 import + 친절한 안내.
8. **버전 헤더.** 각 툴 상단에 `__tool_version__`.

## 디렉토리 (의미별)
- `harness_cli.py` — 통합 CLI 진입점(루트 `./harness` 가 호출).
- `node/` — 노드 단위 작업: 생성/검증/온보딩/재빌드/검증루프/디버그
  (`init_project`·`validate_node`·`gen_onboarding`·`rebuild`·`verify`·`debug_runner`).
- `harness/` — 플랫폼·하네스 와이어링: 진입규칙/스킬 생성, 훅 설치, MCP 와이어링/런처, 세션
  (`gen_agent_rules`·`sync_skills`·`install_hooks`·`wire_mcp`·`mcp_launch`·`session`).
- `data-to-info/` 라우터 + 타입별 변환기(docs/db/code).
- `bootstrap/` 의존성·repo 링크 자동 셋업.
- `lib/` 공용(provenance·embedder·locks·registry 등).
- `hooks/` git 훅(pre-commit·commit-msg·post-merge).
- `tests/` 툴 자체 테스트.

> 모듈은 `ROOT` 기준 경로로 `tools/lib` 등을 찾으므로 위치 독립적이다. `harness_cli.py`/`mcp/server.py`
> 는 `tools/node`·`tools/harness` 를 sys.path 에 추가해 bare import 를 해석한다.

## 새 변환기 추가 (예: json-to-info)
`data-to-info/db/json-to-info/`에 변환기 + `README.md`(입력 스키마, 출력 store, 규칙) 작성하고
`router.py`의 라우팅 테이블에 등록.
