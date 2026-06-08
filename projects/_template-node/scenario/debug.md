---
title: 디버그/배포 시나리오
version: 0.1.0
status: living
target_default: jetson_agx_orin
---
# 디버그 플레이북 (유저가 관리하는 진실 원본)

AI는 이 절차를 읽어 수행한다. 위험 단계는 platform/policies/approval-gates.md 게이트를 통과.

## 절차
1. **규약 로드**: `code/coding_convention/` 읽기.
2. **코딩** → **빌드**. 빌드 산출물 경로를 기록.
3. **타겟 정보 로드**: `hw/<target>.md` (host/user/port/배포경로). 시크릿은 *이름만*.
4. **시크릿 해석**: ssh-agent / vault / env 에서 이름→값 (승인 게이트 + 감사 로그).
5. **접속**: `ssh <user>@<host> -p <port>`.
6. **전송**: `scp <build> <user>@<host>:<deploy_path>` (기본 /root, 시나리오 변수).
7. **실행** → **로그 수집/분석**.
8. 분기:
   - 통과 → 유저 notify.
   - 실패 → 디버그 루프(가설→수정→재시도). 디버그 로직은 env/feature flag로 게이팅.
9. **유저 승인 게이트**.
10. 승인 후 git:
    - 디버그 코드 보존: `git checkout -b <티켓>-<이름>-debug && git commit`.
    - 클린 코드: `<티켓>-<이름>` 브랜치로 디버그 제외분 commit (사람이 "디버그 코드" 확정).
11. worklog 갱신: `history/worklog/<티켓>.md`.

## 변수
- target, deploy_path(기본 /root), build_artifact, ticket_id, ticket_name.
