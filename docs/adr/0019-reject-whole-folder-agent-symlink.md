# 0019. Reject whole-folder `.agent` symlink; keep ADR 0009 projection

- status: accepted
- date: 2026-07-14
- related: ADR 0009 (harness-neutral opt-in), ADR 0008 (enforcement tiers), ADR 0013 (history handover)

## Context

Claude/Cursor 양쪽에 스킬·커맨드 MD를 두고, 루트에 하네스 중립 `.agent/`를 만든 뒤
`.cursor`·`.claude`를 그 폴더로 **통째로 심링크**하자는 제안이 있었다. 목표는 정본 1벌과
새 하네스 연결 단순화다.

## Decision

**채택하지 않는다.** 정본·투영은 ADR 0009를 유지한다.

- 추적 정본: `AGENTS.md`, `platform/skills/*.md`, `platform/commands/*.md`
- 로컬 투영: `harness use` / `sync_skills`가 `.claude/`·`.cursor/` 등 **벤더 네이티브 경로**에
  복제(또는 `--link` 시 파일 단위 심링크)
- 진입규칙만 폴더가 아닌 **파일 심링크**: `CLAUDE.md` / `.cursorrules` → `AGENTS.md`

`.claude` 또는 `.cursor` **디렉터리 전체**를 `.agent`에 심링크하지 않는다.

## Why (whole-folder symlink fails)

벤더 폴더는 공유 MD만이 아니다.

| 경로 | Claude | Cursor | 공유? |
|------|--------|--------|-------|
| `skills/`, `commands/` | 네이티브 | 네이티브 | 가능 |
| `settings.json` | Claude 전용 | 없음 | 불가 |
| MCP 설정 | `.mcp.json`(루트) | `.cursor/mcp.json` | 불가 |
| `rules/*.mdc` | 없음 | Cursor 전용 | 불가 |

통째 심링크는 MCP·권한·rules를 섞거나, 루트 `.agent`를 또 두어 `platform/skills`와
**정본이 두 곳**이 된다(ADR 0009 위반).

## Consequences

- Claude 전용 **추적 MD는 없다** — 스킬/커맨드는 동일 정본의 투영본이다.
- Claude 전용은 JSON/설정(`settings.json`, `headless`)과 MCP 경로뿐.
- 세션 핸드셰이크(`begin_session`)·이력 기록은 **하네스 중립 `AGENTS.md`**에 두고,
  Cursor 전용 `.cursor/rules/*.mdc`에만 두지 않는다.
- 새 하네스 = `platform/harnesses.yaml`에 `rules_file` / `skills_dir` / `commands_dir` 블록 추가.
