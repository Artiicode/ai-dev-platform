# 0009. 하네스 완전 중립 + 옵트인 어댑터 레지스트리

- status: accepted
- date: 2026-06-09
- related: ADR 0008(강제성), ADR 0002(substrate+MCP)

## Context

플랫폼은 "매우 추상적이어서 어떻게 활용하느냐에 따라 사용법이 유연하게 바뀌는" 하네스를 지향한다.
그러나 하네스 고유 지식(Claude/Cursor/Gemini 파일명·경로, 기본 모델 anthropic/claude, adapters/claude-code
커맨드, `.claude`/`.cursor` 산출물)이 코드·추적 파일 곳곳에 박혀 있어 특정 stack에 묶여 있었다.

## Decision

**추적되는 것은 하네스 중립 정본뿐. 하네스 고유 산출물은 단일 옵트인 레지스트리에서 로컬 생성(미추적).**

- 단일 레지스트리 `platform/harnesses.yaml`: harness → {rules_file, skills_dir, commands_dir}, `enabled: []`.
  새 하네스 지원 = 코드 수정 없이 블록 한 개 추가.
- 정본(추적): 진입규칙 `AGENTS.md`(벤더 무관 표준), 스킬 `platform/skills/*.md`, 커맨드 `platform/commands/*.md`.
- 생성물(미추적, `.gitignore`): `enabled` 하네스에 한해 `gen_agent_rules`(진입규칙 심링크)·`sync_skills`
  (스킬/커맨드 투영)가 로컬 생성. 심링크 미지원 OS는 복제 폴백.
- 모델: `models.yaml` 역할 기본 **미설정**(벤더 무전제), 키/모델 명시 시에만 활성(ADR 0008 ③). web-gui
  relay도 `tools/lib/llm.py`(LiteLLM) 경유 — Anthropic 직접 의존 제거.
- `adapters/claude-code/` 제거(커맨드는 중립 `platform/commands/`로, MCP 등록 예시는 `adapters/mcp.example.json`).

## Consequences

- `enabled: []`이면 저장소/clone에 하네스 흔적이 없는 순수 추상 플랫폼. 쓰는 하네스를 켜면 그때 로컬 생성.
- 드리프트 없음(정본 1벌) + 크로스플랫폼 안전(생성물 미추적, 미지원 OS 복제 폴백).
- 레지스트리/CHANGELOG/ADR/문서는 하네스를 *예시/설정*으로만 명명(중립성 유지). MCP는 프로토콜 표준이라 코어 유지.
- 한계: 하네스별 고급 통합(전용 hook 등)은 여전히 그 하네스 어댑터 정의가 필요 — 단 레지스트리로 격리됨.
