# adapters/ — 플랫폼별 어댑터 (L4)
플랫폼 특수성(slash command, hook, 프롬프트 주입 방식)만 흡수. 데이터는 L2 기판에서.
하네스 활성화·생성은 `platform/harnesses.yaml`(레지스트리) + `harness gen-rules`/`sync-skills`가 담당.
- mcp.example.json: MCP 클라이언트 등록 예시(.mcp.json).
- web-gui/: 브라우저 GUI(동일 기판 재사용, 추가 의존성 0).
- generic-api/: MCP 미지원 클라이언트용 파일-컨벤션 폴백.
