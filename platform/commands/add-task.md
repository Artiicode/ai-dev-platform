---
name: add-task
description: 오늘 할 일에 항목 추가 (데일리 스탠드업)
---
사용자가 준 텍스트를 **오늘 데일리 플랜의 [오늘 할 일]** 에 추가한다.

실행:
```
./harness standup --add-task "<사용자 텍스트>"
```
예: `/add-task 오후 2시 Qt 세미나` → `./harness standup --add-task "오후 2시 Qt 세미나"`

- 노드 지정 없이(플랫폼 레벨 개인 플랜, `harness start` 의 subtask 윈도우에 표시)가 기본.
  특정 프로젝트의 작업이면 `./harness standup <node> --add-task "..."`.
- 추가 후 갱신된 목록을 보여준다: `./harness standup --show`.
