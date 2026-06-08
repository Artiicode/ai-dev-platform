---
title: 시크릿 관리 정책
version: 0.1.0
status: living
---
# 시크릿 관리

원칙: **버전관리되는 어떤 파일에도 비밀을 평문 저장하지 않는다.**

- 저장: OS 키체인 / vault / `.env`(gitignore) / `ssh-agent`.
- 참조: 코드·문서엔 *이름만* (예 `api_key_env: ANTHROPIC_API_KEY`, `ssh_key_ref: jetson-orin-key`).
- HW 정보(`projects/*/hw/*.md`)엔 host/user/port/path만. 키/비번 금지.
- `.gitignore`가 `.env`, `*.key`, `*.pem`, `**/secrets/**` 차단.
- 해석(resolve) 시점은 승인 게이트 + 감사 로그 대상.
