---
description: 새 프로젝트 노드 생성(_template-node 복제). ARCHITECTURE §3-4.
---
사용자가 준 프로젝트 이름으로 노드를 만든다:
1. `python tools/node/init_project.py <name> [--link-type path|git-submodule|git-clone] [--url ...] [--ref ...]`
2. 출력된 다음 단계(bootstrap → 인제스트 → MCP 등록)를 사용자에게 안내.
3. link-type 이 git-* 면 `python tools/bootstrap/install.py --node projects/<name>-node` 실행 제안.
