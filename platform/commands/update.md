---
description: data/update/* 를 info/ 로 변환(인제스트). ARCHITECTURE §6.
---
현재 프로젝트 노드의 `data/update/`에 있는 파일을 인제스트한다:
1. `python tools/data-to-info/router.py --node projects/<현재>-node`(먼저 --dry-run으로 라우팅 확인).
2. 변환 결과와 `info/index.yaml` provenance를 사용자에게 요약.
3. 원본을 `archives/`로 이동했는지 확인.
