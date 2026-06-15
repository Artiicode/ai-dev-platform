---
title: "ai-autodev-harness — 아키텍처 설계"
version: 0.10.1
last_updated: 2026-06-08
status: living
audience: [human, ai-agent]
tags: [architecture, harness, multi-agent, mcp, rag, provenance, versioning, security]
summary: >
  여러 AI 에이전트(모델·하네스 무관)가 협업해 소프트웨어 프로젝트를
  개발/테스트/디버그/배포하는 모델-무관(model-agnostic) 자동개발 하네스의 설계.
  핵심 = 지식 기판(파일 진실원본) + MCP 어댑터(고충실도 접근) + 운영 플레이북(시나리오) + ETL/RAG 인제스트.
retrieval_notes: >
  각 H2(## ) 섹션은 self-contained. 프로그래밍적 조회는 향후 docs/architecture-index.json 사용 예정.
  멘탈 모델의 출발점은 docs/learning/harness-curriculum.md (Context + Loop + Gate).
---

# ai-autodev-harness — 아키텍처 설계

> 이 문서는 **사람과 AI 에이전트 둘 다**가 읽도록 설계되었다. 새로 합류하는 에이전트는
> 이 문서 → 작업할 프로젝트의 `projects/<name>-node/history/ONBOARDING.md` 순으로 읽는다.

## 0. 한 줄 정의와 설계 원칙
<a id="overview"></a>

이 플랫폼은 **"단일 LLM을 목표 달성까지 반복 구동시키는 하네스"**(= Context + Loop + Gate,
`docs/learning/harness-curriculum.md`)를 *여러 모델·여러 프로젝트*로 확장한 것이다.

설계를 관통하는 5대 원칙:

1. **기판과 실행을 분리한다(Substrate vs. Harness).** 모델-무관성은 *저장층*이 아니라
   *실행층* 문제다. 데이터/지식은 어디서든 읽히는 파일·DB·벡터(기판)로 두고, 각 AI 플랫폼은
   그 기판을 자기 방식으로 surface하는 *얇은 어댑터*만 갖는다.
2. **진실 원본은 하나, 파생물은 재생성 가능.** `archives/`(원본) + 파이프라인 → `info/`(파생).
   `info/`는 언제든 지울 수 있고 `archives/`로부터 재빌드된다.
3. **출처 추적(provenance)은 1급 시민.** 모든 info 조각은 출처 파일·해시·버전·시각으로 역추적된다.
4. **코드 repo는 깨끗하게.** 산출물 repo에 AI 운영 파일을 넣지 않는다. 둘은 노드 안에서 분리된다.
5. **스택 비종속 + 자동 부트스트랩.** 특정 스택(git, sqlite 등)을 써도 좋되, 선택은 manifest에
   기록되고 `tools/bootstrap`이 재현 가능하게 자동 설치/링크한다.

---

## 1. 계층 구조 (왜 "기판 + 어댑터" 둘 다인가)
<a id="layers"></a>

질문 Q2(코어 노출 방식)에 대한 답은 **둘 다, 계층형**이다. 경쟁이 아니라 동일 데이터를 두 높이에서 노출한다.

```
┌─────────────────────────────────────────────────────────────┐
│  L4  Adapters       MCP / web-gui / (opt-in harnesses)        │  하네스별 얇은 변환
│      (slash command, hook, prompt injection 방식이 제각각)     │
├─────────────────────────────────────────────────────────────┤
│  L3  Access         (a) 파일 컨벤션  ─ 보편 baseline           │  ← 진실 원본
│                     (b) MCP 서버     ─ 고충실도(벡터/SQL/출처)  │  ← 같은 데이터를 질의
├─────────────────────────────────────────────────────────────┤
│  L2  Substrate      md / SQLite / vector  +  index/manifest    │  지식 기판
├─────────────────────────────────────────────────────────────┤
│  L1  Source         archives/ (원본) + repo/ (실제 코드)        │  진실의 뿌리
└─────────────────────────────────────────────────────────────┘
```

**왜 파일 컨벤션을 진실 원본으로 두는가**
- 의존성 0. MCP를 모르는 단순 API 에이전트도 최소한 md/JSON 파일은 읽는다 → *보편 접근 보장*.
- git으로 diff·리뷰·롤백 가능 → 사람과 AI가 같은 변경 이력을 본다.
- MCP 서버가 죽어도 데이터는 남는다.

**왜 MCP 어댑터를 그 위에 올리는가**
- 파일 grep만으로는 대량 코퍼스 시맨틱 검색·정형 데이터 SQL 질의·출처 결합이 비효율.
- MCP는 이미 사실상 표준 인터페이스다 → Claude 및 MCP 지원 클라이언트가 *동일하게* 고품질 접근.
- MCP 서버는 L2 기판을 읽고 쓰는 게이트웨이일 뿐, 별도 데이터를 갖지 않는다(소유권 단일화).

**결론:** 파일 컨벤션 = "항상 동작하는 최저 공통분모", MCP = "지원되는 곳의 가속기". 어댑터(L4)는
하네스 특수성(slash command·hook·프롬프트 주입)만 흡수하며, 활성화는 `platform/harnesses.yaml`.

---

## 2. 디렉토리 구조 (글로벌)
<a id="global-layout"></a>

```
ai-autodev-harness/                 # 플랫폼 루트 (semver로 버전관리)
├── VERSION                         # ai-autodev-harness-v0.1.0
├── CHANGELOG.md                    # 플랫폼 자체 변경 이력
├── README.md
├── platform/                       # ★ 글로벌 AI 설정 (모델-무관 코어)
│   ├── manifest.yaml               #   플랫폼/스키마 버전, 활성 어댑터
│   ├── prompts/                    #   글로벌 시스템/역할 프롬프트
│   ├── context/                    #   글로벌 컨텍스트
│   ├── policies/                   #   승인 게이트·시크릿·안전 정책
│   └── models/models.yaml          #   모델/API 키 추상화 (LiteLLM 스타일, env 참조)
├── tools/                          # data→info 변환기 + 유틸 (버전관리)
│   ├── README.md                   #   ★ 툴 작성 규칙
│   ├── data-to-info/               #   라우터 + 타입별 변환기
│   ├── bootstrap/                  #   의존성·repo 링크 자동 설치
│   └── lib/                        #   provenance 등 공용
├── mcp/                            # 기판을 노출하는 MCP 서버 (L3b 어댑터)
├── adapters/                       # 하네스 접근 어댑터 (L4; 활성화는 platform/harnesses.yaml)
│   ├── mcp.example.json            #   MCP 클라이언트 등록 예시
│   ├── web-gui/                    #   브라우저 GUI(동일 기판 재사용)
│   └── generic-api/                #   MCP 미지원 클라이언트용 폴백
├── docs/
│   ├── ARCHITECTURE.md             #   (이 문서)
│   ├── adr/                        #   플랫폼 자체 설계 결정 기록
│   ├── schemas/                    #   manifest/index JSON Schema
│   └── learning/                   #   harness 학습 커리큘럼(기존 자료)
└── projects/
    ├── _template-node/             #   /init-project 가 복제하는 노드 템플릿
    └── <project>-node/             #   프로젝트별 노드 (아래 §3)
```

---

## 3. 프로젝트 노드 구조 (`<project>-node/`)
<a id="node-layout"></a>

질문 Q3(코드와 노드 관계)에 대한 답: **코드(`repo/`)와 AI 메타데이터를 노드 안에서 분리**하되,
`repo/`를 노드에 붙이는 방식은 manifest의 `link`로 추상화한다(스택 비종속).

```
projects/<project>-node/
├── .git/                  # ★ 노드 메타 자체 git(자동). 플랫폼은 /projects/* 무시 → 이력 완전 분리
├── .gitignore             #   /repo(외부 코드) + 재생성물(vector)·시크릿·캐시 제외
├── manifest.yaml          # 노드 정체성 + repo link 설정 + 스키마 버전 (§4)
├── repo/                  # ★ 실제 코드. AI 파일 절대 금지. 외부 repo 에서 관리(노드 git 미추적)
├── data/update/           # 인제스트 인박스 — 유저가 pdf/img/docx/md/db/code 투입
├── info/                  # ★ 파생물(재생성 가능). AI가 읽는 정보
│   ├── md/                #   소량/권위 문서 (git-diff 가능)
│   ├── db/                #   정형 데이터 (SQLite/DuckDB)  예: 로봇암 x,y,z
│   ├── vector/            #   대량 비정형 텍스트 임베딩 (RAG)
│   ├── wiki/              #   엔티티 위키(평면 슬러그 + type facet + [[링크]] 그래프). INDEX=type별 문서맵, SSOT.md=큐레이션
│   ├── assets/            #   이미지 원본 보존(위키 카드가 참조, 에이전트가 Read로 on-demand 열람)
│   └── index.yaml         #   ★ 라우팅 결정 + provenance 인덱스 (§6)
├── archives/              # ★ 진실 원본. 인제스트에 쓰인 파일 원본 보관
├── context/               # 이 프로젝트에 주입할 큐레이션 컨텍스트
├── skills/                # 프로젝트 전용 스킬 (SKILL.md 포맷 재사용)
├── scenario/              # ★ 유저가 관리하는 운영 플레이북
│   ├── debug.md           #   디버그 절차 (빌드→ssh→scp→실행→로그→커밋, §7)
│   └── test/              #   테스트 시나리오 / 유저 시나리오
├── code/                  # ★ 유저가 관리하는 코딩 규약
│   ├── coding_convention/ #   AI가 plan/verify/implement 시 읽음
│   ├── lint/              #   lint 설정·규칙
│   └── static_analysis/   #   정적분석 규칙
├── hw/                    # 하드웨어 정보 (예 jetson_agx_orin) — ★ 시크릿 참조만, 평문 금지
├── sw/                    # 소프트웨어 환경 정보
├── history/               # ★ 에이전트 연속성: 신규 에이전트가 과거를 이해
│   ├── ONBOARDING.md      #   생성형 진입점(프로젝트 상태 스냅샷). 에이전트가 먼저 읽음
│   ├── adr/               #   프로젝트 설계 결정 기록
│   └── worklog/           #   티켓별 작업·이슈·해결 저널 (append-only)
└── state/                 # 락·스냅샷·진행 커서 (동시성 제어, §8)
```

> 명명 주의: 사용자의 원안 `<project>-node/<project>` 중첩 대신 `<project>-node/repo/`를 권장한다.
> `repo`는 역할이 명확하고 프로젝트명 중복이 없으며, `node`가 graph/k8s/Node.js와 혼동될 여지를
> 줄인다. (단 `-node` 접미사는 원안 유지 — "AI가 관리하는 프로젝트 노드"로 일관 사용.)

---

## 4. 노드 manifest & repo 링크 (스택 비종속 + 자동 부트스트랩)
<a id="manifest-link"></a>

`repo/`를 노드에 연결하는 방식은 4가지를 지원하고, **선택은 manifest에 기록**된다.
`tools/bootstrap/install.py`가 manifest를 읽어 재현 가능하게 자동 셋업한다(질문 Q3 요구사항).

| `link.type` | 의미 | 언제 |
|---|---|---|
| `path` | `repo/`가 그냥 빈 디렉토리 | 단일 폴더로 충분, 별도 VCS 불필요 |
| `git-submodule` | `repo/`가 부모 repo의 submodule | 코드/메타 독립 버전관리(권장 기본값) |
| `git-clone` | 부트스트랩이 지정 URL을 `repo/`로 clone | 코드가 완전 별도 원격 repo |
| `symlink` | `repo/`가 `link.target`(디스크의 기존 프로젝트)으로의 심볼릭 링크 | 코드가 로컬에 이미 존재 → 복제 없이 참조만 |

> `symlink`: 대상은 `link.target`(절대경로 권장; 상대경로는 노드 기준 해석). 대상 미존재 시
> 부트스트랩이 에러로 중단(깨진 링크 방지). 빈 `repo/`는 자동 대체, 비어있지 않으면 수동 정리 요구.
> WSL에서는 네이티브 FS 경로를 쓰고 `/mnt/c/...`는 피한다.

```yaml
# projects/<project>-node/manifest.yaml (발췌)
node:
  name: my_proj
  schema_version: 1          # 이 manifest 포맷 버전 (마이그레이션 키)
  harness_min_version: 0.1.0
link:
  type: git-clone            # path | git-submodule | git-clone
  url: git@github.com:org/my_proj.git
  ref: main                  # 브랜치/태그/커밋
  path: repo
bootstrap:
  package_managers: [pip, npm]   # install.py가 repo 안에서 자동 설치
  setup: ["pip install -e .", "npm ci"]
storage:                         # §6 라우팅 임계값(프로젝트별 오버라이드 가능)
  md_max_chars: 8000
  vector_min_chars: 8000
```

부트스트랩은 멱등(idempotent)해야 한다 — 이미 링크/설치돼 있으면 검증만 하고 통과.

---

## 5. 모델/API 키 무관성
<a id="model-agnostic-keys"></a>

"어떤 AI API 키든 문제없이"라는 요구는 **프로바이더 추상화 설정**으로 푼다. `platform/models/models.yaml`이
*논리적 역할*(planner/coder/verifier/embedder 등)을 *실제 프로바이더·모델·env 키*에 매핑한다.
구현은 **LiteLLM** 같은 기존 라우팅 라이브러리를 권장(재발명 회피, OpenAI/Anthropic/로컬 통일 인터페이스).

```yaml
roles:
  planner:  { provider: anthropic, model: claude-opus,   api_key_env: ANTHROPIC_API_KEY }
  coder:    { provider: anthropic, model: claude-sonnet, api_key_env: ANTHROPIC_API_KEY }
  embedder: { provider: local,     model: bge-m3 }       # 로컬 임베딩(대안 Qwen3-Embedding-0.6B)
```

키는 **절대 파일에 평문 저장 금지** — `*_env`로 환경변수/시크릿 매니저 *참조*만. (§9)

---

## 6. data → info 인제스트 파이프라인 & 저장 라우팅
<a id="ingest"></a>

흐름(질문 Q4 반영):

```
data/update/<아무 확장자>  ──/update──▶  tools/data-to-info/router.py
        │                                       │
        │  1. 파일 타입 감지 + 텍스트 추출        │  pdf/docx→텍스트, img→OCR/비전, db/json→정형
        │  2. 특성 기반 라우팅 (아래 표)          ▼
        │  3. provenance 기록(해시/시각/출처)   info/{md|db|vector} + info/index.yaml
        ▼
   archives/<원본 그대로 + 메타>            ◀── 원본은 진실 원본으로 보관
```

**라우팅 규칙** (특성으로 결정, 단일 저장소 강요 안 함):

| 데이터 특성 | 저장소 | 이유 |
|---|---|---|
| 소량·권위 문서(스펙, 규약, 결정) | **md** (`info/md/`) | 사람이 리뷰·git diff, 토큰 적음, 정확도 우선 |
| 대량 비정형 텍스트(매뉴얼, 논문 묶음) | **벡터 RAG** (`info/vector/`) | 시맨틱 검색, 컨텍스트 절약 |
| 정형 수치/표(로봇암 x,y,z, 센서 로그, BOM) | **SQL** (`info/db/`, SQLite/DuckDB) | 정확한 질의/집계, 스키마 보장 |
| 코드/설정 | repo와 별개로 요약 md + 심볼 인덱스 | 코드 자체는 repo에 있음 |
| 이미지(도면, 사진, 스크린샷) | **위키 카드**(`info/wiki/`) + **원본 보존**(`info/assets/`) | OCR 텍스트 + `![](../assets/..)` 참조. 에이전트가 `Read`로 on-demand 시각 열람(비전 캡셔닝 없음). 무-OCR도 skip 안 됨 |

임계값(`md_max_chars` 등)은 manifest로 오버라이드. 충돌 정보는 **조용히 덮어쓰지 않고** `index.yaml`에
supersedes 관계로 버전을 남긴다.

**프로젝트 간 공유 지식(페더레이션, ADR 0016).** 공통 자료(컨벤션·레퍼런스)는 매 노드에 복제하지 않고
전용 **공유 노드**(예: `_shared-node`)에 한 번만 적재한다. 프로젝트는 manifest `node.shares: [_shared]`로
읽기전용 의존을 선언하고, MCP 검색/읽기가 **자기 `info/` + 공유 노드 `info/`** 를 합쳐 질의한다(거리순 병합,
출처 노드 태깅). 단방향·읽기전용이라 공유 노드는 프로젝트를 보지 않는다. 임베딩 차원은 `models.yaml`로
통일돼 노드/공유 간 호환된다. `platform/`(prompts·policies·skills)이 공통 *설정* 레이어라면, 공유 노드는
공통 *지식*(검색 가능한 info) 레이어다.

**추천 기존 툴체인:** 추출 `unstructured`/`docling`/`markitdown`/`pandoc`(+OCR `tesseract`/비전모델),
정형 `SQLite`/`DuckDB`, 벡터 `sqlite-vec`/`lancedb`/`chroma`, 임베딩 LiteLLM 경유. (로컬 파일 기반 우선 —
git 친화·이식성·오프라인.)

---

## 7. 디버그/배포 시나리오 (HW 타겟 예: Jetson AGX Orin)
<a id="debug-scenario"></a>

사용자 원안 흐름을 **파라미터화된 멱등 플레이북 + 가드레일**로 정식화. 절차는 `scenario/debug.md`가
진실 원본이고, AI는 이를 읽어 수행한다. 단계:

```
규약 로드(code/coding_convention) → 코딩 → 빌드
  → HW/SW 정보 로드(hw/<target>.md: 호스트·계정·경로, 시크릿은 참조名만)
  → 시크릿 해석(ssh-agent/vault/env) → ssh 접근
  → scp로 산출물 → 타겟:/root (경로는 시나리오 변수)
  → 실행 → 로그 수집·분석
  → [통과] 유저 notify  /  [실패] 디버그 루프
  → 유저 승인 게이트
  → 디버그 코드는 <티켓>-<이름>-debug 브랜치 보존
  → 클린 코드 <티켓>-<이름> 으로 add/commit (유저 승인 후)
```

**원안 대비 수정 2가지(중요):**
1. *자격증명 평문 금지.* `hw/jetson_agx_orin.md`에는 host/user/포트/경로만. 비밀번호·키는
   `ssh-agent`나 시크릿 매니저에서 *이름으로* 해석. (§9)
2. *"디버그 코드 AI 자동 제거"는 위험.* AI가 디버그 코드를 식별·삭제하면 오류가 잦다. 권장:
   디버그 로직을 `env`/feature flag로 게이팅하고, 브랜치 보존 후 클린 브랜치는 squash/cherry-pick.
   "무엇이 디버그 코드인가"는 사람 승인 게이트에서 확정.

모든 위험 행동(원격 실행, 커밋, 배포)은 §9의 승인 게이트를 통과해야 한다.

---

## 8. 동시성 & 에이전트 연속성
<a id="concurrency-continuity"></a>

**동시성** — 여러 에이전트가 같은 노드를 동시 작업할 수 있으므로:
- `state/lock.json`으로 노드/티켓 단위 advisory lock.
- 코드 작업은 **git worktree 또는 브랜치 격리** — 에이전트마다 독립 작업트리.
- `info/` 재빌드는 원자적 스왑(temp 생성 후 교체).

**연속성** — 신규 에이전트가 "그전에 어떻게 진행됐는지" 이해(원안 요구):
- `history/worklog/<티켓>.md` = append-only 저널(무엇을·왜·결과·미해결).
- `history/adr/` = 되돌리기 어려운 결정 기록(ADR 포맷).
- `history/ONBOARDING.md` = **생성형 진입점.** 원시 로그가 아니라 현재 상태 요약(활성 티켓,
   최근 결정, 빌드/테스트 상태, 알려진 이슈). 에이전트는 이걸 먼저 읽고 필요 시 worklog로 드릴다운.
- 3층 저장: md(사람 가독) + 이슈 DB(구조화 상태) + 벡터(시맨틱 회상). 외부 트래커(Linear/Jira/
   GitHub Issues)는 MCP로 연동해 재발명 회피 가능.

---

## 9. 보안 · 승인 게이트
<a id="security"></a>

- **시크릿:** 어떤 비밀도 버전관리 파일에 평문 금지. `.env`(gitignore)·OS 키체인·vault·ssh-agent
  사용, 코드/문서에는 *참조 이름만*. `.gitignore`가 `*.key`, `.env`, `**/secrets/**`, `info/vector/*.bin` 차단.
- **승인 게이트(HITL):** `platform/policies/approval-gates.md`가 사람 승인 필수 행동을 정의 —
  원격 실행, 프로덕션 배포, git push, 파일 삭제, 외부 비용 발생 호출, 시크릿 접근.
- **샌드박싱:** 툴 실행은 격리 환경(컨테이너/sandbox), 네트워크는 allowlist.
- **provenance + 감사:** 모든 에이전트 행동·툴 호출을 로깅(관측성/비용 추적 포함).

---

## 10. 버저닝 (다층)
<a id="versioning"></a>

단일 버전이 아니라 **독립적으로 변하는 것들을 각각** 버전관리:

| 대상 | 방식 | 위치 |
|---|---|---|
| 플랫폼(하네스) | SemVer `ai-autodev-harness-vX.Y.Z` | `VERSION` + git tag |
| 플랫폼 변경 이력 | CHANGELOG + ADR | `CHANGELOG.md`, `docs/adr/` |
| 툴 | SemVer(개별 또는 일괄) | 각 툴 헤더/`tools/` |
| 지식 스키마 | `schema_version` 정수 + 마이그레이션 | manifest/index, `docs/schemas/` |
| 노드 상태 | git + worklog | 노드 내부 |
| repo(코드) | 자체 VCS(§4 link) | `repo/` |

스키마가 바뀌면 `schema_version`을 올리고 마이그레이션 스크립트를 제공 → 구버전 노드도 자동 업그레이드.

---

## 11. 플랫폼 자체 개발 이력 (자기 추적)
<a id="self-tracking"></a>

타 에이전트가 *플랫폼 개발 자체*를 이어받을 수 있도록: `CHANGELOG.md`(사용자 대상 변경)와
`docs/adr/`(왜 그렇게 설계했나)를 분리 유지. 모든 비자명 변경은 ADR 한 장 + CHANGELOG 한 줄.
이 ARCHITECTURE.md는 `status: living`으로 frontmatter `version`을 따라간다.

---

## 12. 미해결 / 사용자 결정 대기
<a id="open-questions"></a>

- 임베딩 모델: 로컬(bge-m3 등, 오프라인) vs API. 비용/오프라인 요구에 따라.
- 벡터 스토어 확정: `sqlite-vec`(단일 파일, 최소 의존) vs `lancedb`/`chroma`(기능 풍부).
- 외부 이슈 트래커 연동 여부(자체 worklog만 vs Linear/Jira MCP).
- GUI 계획: 1차 타깃은 Linux/WSL CLI(`harness`). 추후 웹 GUI는 동일 MCP 서버를 `--transport sse`로 재사용한다(adapters/web-gui). 새 데이터 계층 없음.
- 멀티 에이전트 오케스트레이션 깊이: 단순 worktree 격리 vs 중앙 스케줄러/큐.

---

## changelog
<a id="changelog"></a>

- **0.1.0 (2026-06-08)** — 초기 아키텍처. 계층(기판+MCP) 모델, 노드/글로벌 레이아웃, manifest link,
  인제스트 라우팅, 디버그 시나리오, 보안/게이트, 다층 버저닝 정의.
