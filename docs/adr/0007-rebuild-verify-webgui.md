# ADR 0007 — rebuild · verify · 웹 GUI 백엔드
- 상태: accepted · 날짜: 2026-06-08
## 결정
- rebuild.py: info/ 를 비우고 archives/ 에서 router 재실행으로 완전 재생성("파생물=재생성 가능" 실증).
- verify.py: code/verify.yaml(checks: name/cmd/required/cwd) 실행 → state/verify-report.md, 필수 실패 시 exit≠0.
  Plan→Act→Observe→Verify 루프의 Verify 단계를 노드별로 선언적으로 정의.
- adapters/web-gui/server.py: stdlib http 스켈레톤. mcp/server.py 도구 재사용(새 데이터 계층 없음).
  /api/info·search·query·chat. chat 은 RAG 컨텍스트 조립 + (ANTHROPIC_API_KEY 있으면) 모델 relay, 없으면 스텁.
- 임베딩: bge-m3(SentenceTransformer) 실제 백엔드 경로 검증, 미설치 시 hash 폴백.
## 결과
지식 재현성 + 선언적 검증 + 브라우저 접근(동일 기판) 확보. 웹 GUI 는 sse(MCP) 또는 이 HTTP 백엔드 둘 다 가능.
