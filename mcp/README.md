# mcp/ — 기판 노출 MCP 서버 (L3b 어댑터)

L2 기판(info/ 의 md·sql·vector + index.yaml)을 MCP 도구로 노출하는 게이트웨이.
자체 데이터 소유 없음 — 파일/DB를 읽을 뿐. MCP 지원 클라이언트(하네스 무관)가 동일 접근.

## 노출 도구
| 도구 | 설명 |
|---|---|
| `list_info()` | 이 노드의 md 파일/sql 테이블/벡터 청크 수 요약 |
| `search_info(query, k)` | 벡터 RAG 시맨틱 검색(로컬 bge-m3), 출처 포함 |
| `query_sql(sql, db?)` | info/db/*.sqlite 읽기 전용 SQL (모든 db ATTACH) |
| `read_md(name)` | info/md/<name> 원문 |
| `get_provenance(entry_id?)` | info/index.yaml 출처 기록 |

## 실행
```bash
pip install -r ../requirements.txt
NODE_DIR=../projects/<name>-node python server.py     # stdio MCP 서버
# 오프라인/테스트: HARNESS_EMBED_BACKEND=hash 추가
```
대상 노드는 `NODE_DIR` 환경변수로 지정한다(노드마다 서버 1개).

## 클라이언트 등록 (MCP 클라이언트 .mcp.json)
`adapters/mcp.example.json` 참고. NODE_DIR 를 프로젝트 노드 경로로.
