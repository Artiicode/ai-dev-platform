# ADR 0004 — 인제스트 추출 파이프라인 + init-project
- 상태: accepted · 날짜: 2026-06-08
## 맥락
data/update 에 pdf/docx/html/이미지 등 다양한 포맷이 들어온다. router 가 텍스트를 못 다루면 무의미.
## 결정
- tools/lib/extractor.py: pdf(pypdf)/docx(python-docx)/html(bs4)/이미지(pytesseract OCR) → 텍스트.
  의존성은 선택적 — 부재 시 (None, 사유)로 graceful degrade 하고 router 가 해당 파일을 skip+보고.
- router: 추출 후 텍스트 길이로 md/vector 재결정(정형은 그대로 sql). 원본은 archives 보존.
- tools/init_project.py: _template-node 복제로 <name>-node 생성, manifest 치환, 다음 단계 안내.
## 결과
어떤 포맷이든 인제스트 가능. 새 프로젝트 온보딩이 한 명령.
