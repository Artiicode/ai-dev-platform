# history/standup — 일(day) 단위 스탠드업 / 할 일 로그

스크럼/스탠드업용 일일 기록. 파일은 `YYYY-MM-DD.md`, 모두 **리스트** 형식:

```
## [오늘 할 일]
- [ ] 오후 2시 Qt 세미나        # /add-task 로 추가, 완료 시 - [x]

## [진행사항]
- [HH:MM] 무엇을 진행 중인지 (작업하며 수시로 추가)

## [요약]
- 오늘: 오늘 진행 중인 것
- 내일: 내일 할 예정
```

- 오늘 파일이 없으면 자동 생성하며, **전날 파일의 미완료 항목(`- [ ]`) + [요약] '내일'** 을 오늘
  [오늘 할 일]로 **carry-over**. 아무것도 없으면 `- 없음`.
- 관리(에이전트가 수시/일괄/요청 시):
  - 할 일:  `./harness standup <node> --add-task "..."`
  - 진행:   `./harness standup <node> --add "..."`
  - 요약:   `./harness standup <node> --today "..." --tomorrow "..."`
  - 보기:   `--show [--date YYYY-MM-DD]` · 목록 `--list`
  - MCP:    `standup_add` / `standup_summary` (세션 토큰 필요)
- 오늘 분은 `history/ONBOARDING.md`(자동 인계서)에도 요약되어 다음 에이전트가 바로 본다.

> 노드 없이 `./harness standup ...` 은 **플랫폼 레벨 개인 일일 플랜**(`<루트>/standup/`, 미추적)을 다루며
> `harness start` 의 `subtask` 윈도우에 표시된다.
