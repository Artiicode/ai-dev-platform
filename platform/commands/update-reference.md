---
description: 노드 data/update/ 의 참조 자료를 종류에 맞춰 info(SQL/RAG/md)로 인제스트.
---
대상 노드의 `data/update/`에 올라온 참조 자료를 변환한다(`harness ingest <node>`):

- **숫자·표·불변/멱등 데이터**(json/csv 등) → `info/db/*.sqlite` (SQL, 정확 질의)
- **큰 문서 / 에이전트가 검색·인용할 텍스트** → `info/vector/store.db` (RAG)
- **작고 권위 있는, 통째로 읽어도 컨텍스트 부담 없는 자료** → `info/md/`

원본은 `archives/`로 보존, 출처·해시는 `info/index.yaml`에 기록(임계값은 노드 `manifest.storage`로 조정).

절차:
1. 대상 노드의 `data/update/`에 파일이 있는지 확인(없으면 사용자에게 업로드 위치 안내).
2. `harness ingest <node>` 실행(먼저 `--dry-run`으로 라우팅 확인 권장).
3. `info/index.yaml` provenance와 산출(SQL/RAG/md) 요약을 사용자에게 보고. 원본이 `archives/`로 갔는지 확인.
4. `harness validate <node>` 통과 확인 후, 경과를 `history/worklog/<티켓>.md`에 기록.
