# ADR 0005 — Linux/WSL 1차 타깃, 통합 CLI, MCP 트랜스포트
- 상태: accepted · 날짜: 2026-06-08
## 맥락
사용자는 주로 Linux/WSL에서 실행하고, Windows는 추후 웹 GUI로 접속한다.
## 결정
- 통합 CLI `harness`(tools/harness_cli.py) + 루트 런처. venv 자동 사용.
- scripts/setup.sh(venv+deps+tesseract), Makefile, .env.example 로 Linux/WSL 셋업 표준화.
- MCP 서버 트랜스포트 선택: stdio(기본·CLI·Claude Code) | sse | streamable-http(env HARNESS_MCP_TRANSPORT).
  웹 GUI는 같은 서버를 sse로 재사용(adapters/web-gui) — 새 데이터 계층 없음.
- 노드는 WSL 네이티브 FS 권장(마운트 sqlite I/O 회피).
## 결과
Linux/WSL 네이티브 UX 확보, 웹 GUI 경로 예약. 동일 기판/도구를 CLI·Claude·GUI가 공유.
