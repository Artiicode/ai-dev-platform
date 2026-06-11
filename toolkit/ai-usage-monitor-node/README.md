# ai-usage-monitor (toolkit node)

번들된 **플랫폼 도구**입니다. 유저 프로젝트 노드(`projects/*`, git 미추적)와 달리 `toolkit/` 의 도구
노드는 **버전관리(추적)** 되어 플랫폼과 함께 배포·진화합니다. 형태는 projects 호환(`repo/` + `manifest.yaml`).

- 코드: `repo/`(원본을 **하드 복사** — 심링크 아님). 출처는 `manifest.yaml` 의 `origin`.
- 실행(터미널 대시보드):
  ```bash
  ./harness tool ai-usage-monitor -- --watch 5     # 5초 주기 자동 갱신
  ./harness tool ai-usage-monitor -- --json        # 1회 JSON
  ```
  `harness tool` 은 플랫폼 venv 로 `python -m ai_usage_monitor.cli` 를 `PYTHONPATH=repo` 로 실행합니다.
- 의존성: CLI(`--watch`)는 `requests`(+stdlib)만 필요(플랫폼 venv 에 포함). PySide6 는 GUI(`run.py`) 전용.
- 업데이트: 상류 도구가 바뀌면 `repo/` 를 다시 하드 복사하고 커밋(플랫폼 이력에 남김).
