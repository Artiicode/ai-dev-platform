# ADR 0001 — 아키텍처 결정 기록(ADR)을 사용한다
- 상태: accepted · 날짜: 2026-06-08
## 맥락
타 AI 에이전트가 플랫폼 개발을 이어받을 때 "왜 이렇게 설계했는가"가 필요하다.
## 결정
되돌리기 어려운 모든 설계 결정을 `docs/adr/NNNN-*.md`(플랫폼)와 `projects/*/history/adr/`(프로젝트)에
ADR 한 장으로 남긴다. 사용자 대상 변경 요약은 CHANGELOG.md로 분리.
## 결과
이력이 사람·AI 모두에게 검색·인용 가능. ARCHITECTURE.md는 living 문서로 version을 따른다.
