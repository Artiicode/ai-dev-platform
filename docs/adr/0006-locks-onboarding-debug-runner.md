# ADR 0006 — 동시성 락 · 승인 게이트 · 온보딩 생성 · 디버그 러너
- 상태: accepted · 날짜: 2026-06-08
## 맥락
멀티 에이전트 연속성/안전을 위해 (a) 충돌 방지 (b) 위험 행동 통제 (c) 빠른 컨텍스트 회복이 필요.
## 결정
- locks.py: state/lock.json 원자적(O_EXCL) advisory 락 + stale(프로세스 사망/TTL) 자동 회수.
- approval.py: 승인 게이트(HITL). HARNESS_AUTO_APPROVE=1(자동화) | TTY 대화 | 그 외 차단. state/audit.log 감사.
- worktree.py: git worktree 로 에이전트별 작업 격리(브랜치).
- gen_onboarding.py: worklog/adr/info/manifest → ONBOARDING.md(현재 상태 스냅샷, 결정적·멱등).
- debug_runner.py: scenario/debug 플레이북 구동. dry-run 기본, --execute 시 락+단계별 승인. 시크릿 이름참조만.
## 결과
안전한 원격 디버그/배포 + 멀티 에이전트 동시 작업 + 신규 에이전트 즉시 온보딩.
