# platform/skills — 정본 스킬 레지스트리 (하네스 중립)

재사용 스킬을 **하네스 중립 마크다운 1벌**로 여기 정의한다. `tools/sync_skills.py`
(`harness sync-skills`)가 각 AI 하네스의 네이티브 위치로 배포한다:

- `.claude/skills/<slug>/SKILL.md` (Claude Code)
- `.cursor/skills/<slug>/SKILL.md` (Cursor)

규칙:
- 파일명 `<slug>.md`. 상단에 `name`/`description` frontmatter(SKILL.md 규격) 권장.
- `_template.md`를 복사해 새 스킬 작성. `README.md`/`_template.md`/`INDEX.md`는 배포에서 제외.
- 노드 전용 스킬은 `projects/<name>-node/skills/<slug>.md`에 두고 `harness sync-skills --node <name>`.
- 배포는 기본 **복제**(이식성). POSIX에서 단일 원본을 원하면 `--link`(심볼릭 링크).

특정 stack/플랫폼 의존을 피하기 위해, 스킬 본문은 하네스 고유 문법 대신 일반 지침으로 작성한다.
