---
title: "AI Harness Engineering — 학습 커리큘럼"
version: 0.8.0
last_updated: 2026-06-08
status: living
audience: [human, ai-agent]
tags: [ai-harness, agent, scaffolding, agent-loop, context-layer, mcp, rag, curriculum]
summary: >
  단일 LLM을 목표 달성까지 반복 구동시키는 "하네스(scaffolding)" 골격을 단계적으로
  학습하기 위한 살아있는 문서. 하네스 = Context layer + Agent loop + Human gate 세 축으로 구성.
  최종 목표: CLI 우선(추후 GUI) 에이전틱 소프트웨어 엔지니어링 플랫폼 설계.
retrieval_notes: >
  각 H2(## ) 섹션은 독립적으로 청크 가능하도록 self-contained하게 작성됨.
  각 섹션은 바로 아래에 <a id="..."> 안정적 anchor를 가진다 — 직접 참조/딥링크용.
  프로그래밍적 조회는 동봉된 harness-index.json 매니페스트를 사용할 것.
---

# AI Harness Engineering — 학습 커리큘럼

> 이 문서는 **사람과 AI 에이전트 둘 다**가 읽도록 설계되었다.
> 사람은 위에서 아래로 읽고, AI 에이전트는 frontmatter 메타데이터 →
> `harness-index.json` → 필요한 섹션 anchor 순으로 retrieve하면 된다.

## 0. 이 문서 사용법 (navigation)
<a id="how-to-use"></a>

- **사람**: `## 1`부터 순서대로 읽기. 로드맵(`## roadmap`)에서 다음에 채울 주제를 고른다.
- **AI 에이전트**: `harness-index.json`의 `sections` 배열에서 `tags`/`summary`로 후보 섹션을 찾고, 해당 `anchor`로 이 문서의 한 섹션만 정확히 가져온다.
- **버저닝**: 이 문서 자체는 frontmatter의 `version`(semver)으로 관리된다. 변경 이력은 `## changelog`.
- **status 값**: `done`(작성 완료) · `planned`(예정 stub) · `living`(계속 갱신).

---

## 1. 핵심 멘탈 모델 — 하네스 = Context + Loop + Gate
<a id="lesson-1-core-model"></a>
**status:** done · **lesson:** 1

### 1.1 하네스란 무엇인가
"하네스(harness / scaffolding)"는 **모델 그 자체가 아니라 모델을 둘러싼 바깥 엔지니어링**이다.
같은 모델을 쓰더라도 결과 품질을 좌우하는 골격. 핵심 통찰:

> 모델은 한 번에 한 스텝만 똑똑하게 처리한다.
> 하네스는 그 모델을 **목표 달성까지 반복 구동**시키는 루프다.

### 1.2 동작 루프 (6단계)
입력과 컨텍스트 수집 후, 보라색 4단계(Plan→Act→Observe→Verify)가
요구사항을 만족할 때까지 반복되고, 통과하면 결과를 출력한다.

```
Input → Context assembly → [ Plan+confirm → Act → Observe → Verify ] → Done
                                    ^___________________________|
                                     Verify가 "아직"이면 루프 백
```

### 1.3 각 단계 정의

- **Input** — 사용자의 요청.
- **Context assembly** — 모델에게 "무엇을 보여줄지" 결정. 컨텍스트 창은 유한하므로
  프로젝트 전체가 아니라 관련된 것만 선별해 넣는다. (하네스 품질의 큰 비중)
- **Plan + confirm** — 작업을 잘게 분해하고, 위험·모호하면 사람에게 먼저 묻는 게이트
  (human-in-the-loop).
- **Act** — 실제 행동. tool use(파일 편집, 명령 실행)와, 큰 작업이면 서브에이전트에 위임.
- **Observe** — 행동 결과를 다시 읽어들임 (테스트 통과 여부, 에러, 출력).
- **Verify** — "요구사항/의도대로 됐나?" 채점. 통과 시 Done, 아니면 Plan으로 루프 백.

### 1.4 세 축 요약
| 축 | 역할 | 대응 단계 |
|---|---|---|
| Context layer | 무엇을 모델에게 보여줄지 | Context assembly |
| Agent loop | 끝까지 물고 늘어지는 반복 | Plan · Act · Observe · Verify |
| Human gate | 사람 컨펌·통제 | Plan + confirm |

---

## 2. 개념 ↔ 실제 사례 ↔ 내 플랫폼 매핑
<a id="lesson-1-mapping"></a>
**status:** done · **lesson:** 1

> 주의(정확도 경계): 아래 "Claude Code류" 칸은 **공개적으로 알려진 동작 / 일반적인
> agentic 코딩 툴 패턴** 수준이다. 정확한 내부 사양은 공식 문서로 검증할 것
> (예: https://docs.claude.com/en/docs/claude-code ).

| 하네스 단계 | 개념 | Claude Code류 사례 | 내 플랫폼에서 |
|---|---|---|---|
| Context assembly | 관련 컨텍스트 선별 | 프로젝트 컨텍스트 파일(예 `CLAUDE.md`), 파일트리·검색 | **핵심.** DB/Embedding/md retrieve + MCP 표준화로 타 에이전트도 접근 |
| Plan + confirm | 분해·사람 컨펌 | 실행 전 계획 제시, 위험 명령 승인 요구 | "AI가 먼저 확인·플래닝·컨펌" 요구사항 |
| Act | tool use·위임 | 파일 편집/명령 실행, subagents 위임 | code/test/debug/deploy = 도구 or 전용 서브에이전트 |
| Observe | 결과 수집 | 테스트·에러 출력 읽기 | 동일 |
| Verify | 요구사항 채점 | 검증 루프 | "요구사항대로·의도한대로" = Verify 품질 |

---

## roadmap — 다음에 채울 주제
<a id="roadmap"></a>

| # | 주제 | anchor (예정) | status |
|---|---|---|---|
| A | Context 레이어 (MCP / RAG / 임베딩) | `#topic-context-layer` | planned |
| B | Loop 설계 (Plan·Act·Observe·Verify 구현) | `#topic-loop-design` | planned |
| C | 서브에이전트 (위임 / 오케스트레이션 구조) | `#topic-subagents` | planned |
| D | Verify / 평가 (요구사항대로를 어떻게 채점) | `#topic-verification` | planned |

---

## glossary — 용어집
<a id="glossary"></a>

- **harness / scaffolding**: 모델을 둘러싼 제어·컨텍스트·도구·검증 골격.
- **agent loop**: Plan→Act→Observe→Verify를 목표 달성까지 반복하는 구조.
- **tool use**: 모델이 외부 행동(파일 편집, 명령 실행 등)을 호출하는 능력.
- **subagent**: 별도 컨텍스트/도구/시스템 프롬프트를 가진, 위임받은 하위 에이전트.
- **human-in-the-loop (HITL)**: 위험·모호한 결정에 사람 컨펌을 끼워넣는 게이트.
- **MCP (Model Context Protocol)**: 에이전트/툴이 표준 방식으로 데이터·도구에 접근하는 프로토콜.
- **RAG**: 검색으로 관련 문서를 찾아 컨텍스트에 주입하는 방식.

---

## changelog
<a id="changelog"></a>

- **0.1.0 (2026-06-08)** — 문서 생성. Lesson 1(핵심 멘탈 모델 + 3-way 매핑) 작성.
  로드맵 A~D stub 추가. 용어집·인덱스 매니페스트 동봉.
