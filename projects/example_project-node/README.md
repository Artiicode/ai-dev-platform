# 프로젝트 노드 템플릿 (_template-node)
`/init-project <name>` 시 이 폴더를 `projects/<name>-node/`로 복제하고 manifest의 REPLACE_ME를 채운 뒤
`python tools/bootstrap/install.py --node projects/<name>-node` 로 repo 링크/의존성 설치.
구조 설명: ../../docs/ARCHITECTURE.md §3.
