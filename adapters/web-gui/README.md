# web-gui 어댑터 (예정)

Windows 등에서 브라우저로 이 플랫폼과 대화하는 웹 GUI. **새 데이터 계층을 만들지 않는다** —
기존 MCP 서버(`mcp/server.py`)와 동일 L2 기판을 재사용한다.

## 계획
- 트랜스포트: MCP 서버를 `HARNESS_MCP_TRANSPORT=sse`(또는 streamable-http)로 띄워 브라우저/백엔드가 접속.
  `harness serve <node> --transport sse`
- 백엔드: 얇은 HTTP 레이어가 채팅 UI ↔ 모델(models.yaml/LiteLLM) ↔ MCP 도구를 중계.
- 노출: search_info / query_sql / read_md / get_provenance / list_info 를 그대로 GUI 패널로.
- 승인 게이트(platform/policies/approval-gates.md)는 GUI 버튼으로 표면화.
