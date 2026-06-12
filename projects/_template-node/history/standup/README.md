# history/standup — 일(day) 단위 스탠드업 로그

스크럼/스탠드업용 일일 기록. 파일은 `YYYY-MM-DD.md`, 형식:

```
## [진행사항]
- [HH:MM] 무엇을 진행 중인지 (작업하며 수시로 추가)

## [요약]
- 오늘: 오늘 진행 중인 것
- 내일: 내일 할 예정
```

관리(에이전트가 수시/일괄/요청 시):
- 추가:   `./harness standup <node> --add "API 인증 리팩터 진행"`
- 요약:   `./harness standup <node> --today "인증 리팩터" --tomorrow "테스트 작성"`
- 보기:   `./harness standup <node> --show [--date YYYY-MM-DD]` · 목록 `--list`
- MCP:    `standup_add` / `standup_summary` (세션 토큰 필요)

오늘 스탠드업은 `history/ONBOARDING.md`(자동 인계서)에도 요약되어, 다음 에이전트가 바로 본다.
