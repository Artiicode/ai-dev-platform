---
description: conventions/verify.yaml 체크 실행(lint/types/unit/scenario). Plan→Verify 의 Verify.
---
`python tools/harness_cli.py verify <name>` 실행. 필수 체크 실패 시(exit≠0) 원인과
`state/verify-report.md`를 사용자에게 보고하고 수정 계획을 제안. 통과하면 다음 단계 진행.
