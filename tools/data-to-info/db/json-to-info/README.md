# json-to-info 변환기 규칙
- 입력: `data/update/*.json` (정형 데이터, 예: 로봇암 좌표 배열).
- 출력 store: **sql** (`info/db/<name>.sqlite`). 키-값 단순 문서는 md 가능.
- 규칙: 스키마 추론 → 테이블 생성 → upsert. 숫자/타임스탬프 타입 보존.
- provenance: `tools/lib/provenance.py`로 source/sha256/시각 기록.
- 멱등: 동일 sha면 skip. 변경 시 supersedes로 이전 entry 연결.
