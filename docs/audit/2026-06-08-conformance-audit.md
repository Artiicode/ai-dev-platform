---
title: 설계 요구사항 적합성 감사 (Conformance Audit)
date: 2026-06-08
platform_version: ai-autodev-harness-v0.6.0
status: accepted
audience: [human, ai-agent]
related: [docs/ARCHITECTURE.md, docs/audit/2026-06-08-remediation-plan.md]
---

# 설계 요구사항 적합성 감사

원안 설계 프롬프트(플랫폼 창립 요구사항)와 추가 강조사항("타 AI Agent에게 **강제성** 주입")
대비, v0.6.0 구현 상태를 영역별로 정밀 감사한 결과. 수정 계획은
[remediation-plan](2026-06-08-remediation-plan.md) 참조.

## 0. 한 줄 결론

설계 문서와 **기판(substrate: 파일/DB/벡터)** 은 견고하나, 핵심 요구인 **"강제성"이 사실상
미구현**이다. 현재 플랫폼은 *강제 시스템*이 아니라 **자율준수(honor-system) 기반 문서 시스템**이다.
보편적(모델·하네스 무관) 강제 지점이 없는 것이 최대 결함.

## 1. 요구사항별 적합성 요약

| # | 요구사항 | 상태 | 핵심 근거 |
|---|---|---|---|
| 1 | `<name>-node/repo/` 구조, AI데이터는 `-node/` 레벨 | ✅ 적합 | 원안 중첩 대신 `repo/` 채택, ADR에 이유 문서화 |
| 2 | `repo/`에 AI 파일 금지 | ✅ 적합 | `repo/` 비어있음, AI데이터 전부 `-node/` 레벨 |
| 3 | 프로젝트별 coding/test/debug 파일 | ⚠️ 85% | `project_A-node/code/verify.yaml` 누락(생성 버그) |
| 4 | 디버그 시나리오(빌드→hw→ssh→scp→commit) | ✅ 적합 | `scenario/debug.md` 11단계 + 시크릿 참조명 + 승인 게이트 |
| 5 | 이력/이슈/해결 기록(새 에이전트 인계) | ✅ 적합 | ONBOARDING + worklog(append-only) + adr + provenance + RAG |
| 6 | data→info 파이프라인(임의 확장자→md/SQL/RAG) | ⚠️ 골격만 | 라우터는 동작하나 변환기 프레임워크가 빈 껍데기 |
| 7 | tools 작성 규칙 관리 | ⚠️ 부분 | 가이드 문서는 있으나 등록 메커니즘 없음 |
| 8 | 플랫폼 버저닝(ai-autodev-harness-vX.Y.Z) | ✅ 적합 | VERSION + Keep-a-Changelog + SemVer |
| 9 | 플랫폼 자체 개발 이력 추적 | ✅ 적합 | CHANGELOG + ADR 7개 |
| 10 | 모델/API 무관성 | ⚠️ 설계만 | 기판은 무관, 실행층은 Claude 전용·LiteLLM 미통합 |
| **11** | **타 AI Agent 강제성 주입** | 🔴 **미구현** | 전부 평문 문서, 주입·게이팅 메커니즘 없음 |

## 2. 🔴 핵심 결함 — 강제성 부재 (요구 #11)

원안과 추가 요구 모두 "타 AI Agent에게 강제성 주입"을 요구하나, 현재는 **전부 '읽어주길 바라는 문서'**.

| 메커니즘 | 위치 | 실제 강제력 |
|---|---|---|
| 공통 규칙 | `platform/prompts/global-system.md` | ❌ 평문. 어떤 에이전트 컨텍스트에도 주입 안 됨 |
| 온보딩 | `history/ONBOARDING.md` | ❌ "먼저 읽어라" 권고. 무시하고 작업 가능 |
| 승인 게이트 | `tools/lib/approval.py` | ⚠️ `harness` CLI 흐름에서만 동작 (~5%) |
| MCP 서버 | `mcp/server.py` | ❌ 인증·게이팅 0. 읽기 도구 5개뿐, **쓰기 게이트 없음** |
| 슬래시 커맨드 | `adapters/claude-code/commands/*.md` | ❌ 실제 플러그인 아님, 단순 markdown 설명 |

- **루트에 `CLAUDE.md` 부재** — 현재 유일 사용 하네스(Claude Code)조차 규칙 자동주입 안 됨.
- **非Claude 에이전트(Cursor/Gemini/API)에는 주입 지점이 0개.**
- MCP 도구는 읽기 전용 5개(`list_info`/`search_info`/`query_sql`/`read_md`/`get_provenance`).
  기판 *변경*은 파일시스템 직접 쓰기로 일어나 검증을 전혀 안 거침.

### 진단
임의의 외부 AI를 *프롬프트로* 100% 강제하는 것은 불가능. 진짜 강제는 **기계적 경계
(artifact boundary)** 에서만 가능하다. 권장 3계층(의존성 계층화)은 remediation-plan 참조.

## 3. ⚠️ 모델/API 무관성 (요구 #10) — 설계만, 실행층은 Claude 전용

- 기판(파일/DB/벡터)은 진정한 model-neutral. ✅
- `platform/models/models.yaml`은 이미 `provider/model/api_key_env` 형태의 **LiteLLM 스타일
  스키마**를 갖췄으나(설정은 OK), **그 설정을 호출하는 LiteLLM 실행층이 없음**. 역할은 전부
  anthropic/claude로만 채워짐.
- `adapters/generic-api/`는 **README만 존재, 미구현**. Cursor/Gemini/OpenAI/Ollama 어댑터 0개.
- 非Claude 모델 end-to-end 동작을 증명한 적 없음.

## 4. ⚠️ data→info 변환기 프레임워크 (요구 #6, #7) — 골격만

- 라우터(`tools/data-to-info/router.py`)는 동작: 추출(pdf/docx/html/OCR)→길이 기반 md/vector,
  구조데이터→SQL, provenance 기록 + `archives/` 이동.
- 그러나 `tools/data-to-info/{db,code,docs}/`는 거의 빈 껍데기. `db/json-to-info/`도 README뿐,
  실제 로직은 `router.py`에 인라인.
- **변환기 등록 메커니즘 없음** — 새 변환기 추가 = `router.py` 직접 수정 (원안의 "tools 규칙 관리"와 상충).
- 코드 파일(`.py`/`.js`) 전용 핸들러 없음(원안은 코드→요약+심볼 인덱스 언급).
- 청킹이 문자 기반(토큰 비인식). 미지 확장자는 조용히 md 폴백(명시적 거부 없음).

## 5. 🟡 구체적 버그·불일치 (검증 완료)

| ID | 항목 | 사실 | 위치 |
|---|---|---|---|
| B1 | `verify.yaml` 누락 | 템플릿엔 있으나 project_A에 미생성 | `projects/project_A-node/code/` |
| B2 | 스키마 런타임 미검증 | `jsonschema` 설치됐으나 **어떤 .py도 import 안 함**. manifest 오타가 KeyError로 조용히 깨짐 | `tools/bootstrap/install.py` 등 |
| B3 | 문서 버전 드리프트 | ARCHITECTURE=0.1.0, USAGE=0.5.0 vs 플랫폼 0.6.0 | `docs/ARCHITECTURE.md:3`, `docs/USAGE.md:3` |
| B4 | 데모 미실행 | project_A `data/update/`에 4개 파일 있으나 `archives/`·`index.yaml` 비어있음 | `projects/project_A-node/` |
| B5 | 빈 디렉토리 | `scenario/debug/` 목적 불명(파일 `debug.md`와 공존) | `projects/_template-node/scenario/` |
| B6 | 커리큘럼 미완 | Lesson 1만 작성, 로드맵 A–D 스텁 | `docs/learning/harness-curriculum.md` |
| B7 | 마이그레이션 부재 | `schema_version:1` 증가 시 마이그레이션 도구/문서 없음 | 전반 |

## 6. 감사 방법

영역별 read-only 병렬 탐색 4건(노드구조 / data→info / 강제성·모델무관성 / MCP·버저닝·docs) 후
load-bearing 사실(MCP 도구 목록, models.yaml, jsonschema 미사용, verify.yaml 누락, 버전 드리프트)을
직접 재확인. 본 감사는 코드를 수정하지 않음(읽기 전용).
