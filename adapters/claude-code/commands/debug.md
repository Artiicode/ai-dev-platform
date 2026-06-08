---
description: scenario/debug 플레이북 구동(빌드→ssh→scp→실행→로그→커밋). ARCHITECTURE §7.
---
1. 먼저 dry-run: `python tools/harness_cli.py debug <name> --ticket <T> --name <n> --build <path> --run-cmd "<cmd>"`
   으로 계획(scp/ssh 명령, git 분기)을 사용자에게 보여준다.
2. 사용자가 승인하면 `--execute` 추가. 위험 단계마다 승인 게이트가 적용된다(원격 실행/전송/커밋).
3. 종료 후 worklog 갱신 및 `onboard` 재생성 제안.
