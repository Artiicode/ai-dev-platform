---
name: update-info
description: data/update/ 에 들어온 임의 포맷 파일을 검증 가능한 info(md/SQL/vector)로 변환할 때 사용.
---

# update-info — 데이터 → 정보 인제스트

## 언제
- 사용자가 노드 `data/update/`에 파일(pdf/docx/html/img/json/csv 등)을 넣고
  "정보 업데이트", "/update", "인제스트" 등을 요청할 때.

## 절차
1. 대상 노드 확인 후 `data/update/`에 파일이 있는지 본다.
2. `harness ingest <node>` 실행(오프라인/테스트는 `HARNESS_EMBED_BACKEND=hash`).
   - 구조 데이터(json/csv) → `info/db/*.sqlite`
   - 큰 텍스트 → `info/vector/store.db`(RAG), 작은 권위 문서 → `info/md/`
   - 원본은 `archives/`로 이동, 출처·해시는 `info/index.yaml`에 기록.
3. `harness info <node>`로 산출물 요약, `harness search <node> "<질의>"`로 검색 확인.
4. `harness validate <node>`로 적합성 확인 후, 경과를 `history/worklog/<티켓>.md`에 기록.

## 주의
- `info/`에 직접 쓰지 말고 인제스트 경로(또는 MCP `ingest_data`)를 쓴다(provenance 보장).
- 검색은 인제스트와 **같은 임베딩 백엔드**를 사용해야 한다.
