# ai-autodev-harness — Linux/WSL 편의 타깃
.PHONY: setup ready test clean init ingest serve info
PY := $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
NODE ?=
NAME ?=

setup:            ## venv + 의존성 + tesseract 안내
	bash scripts/setup.sh

ready:            ## git clone 후 사용준비(멱등): venv + 훅 + 벡터 재생성
	bash scripts/post_clone.sh

init:             ## 새 노드:  make init NAME=my_proj
	$(PY) tools/harness_cli.py init $(NAME)

ingest:           ## 인제스트:  make ingest NODE=my_proj
	$(PY) tools/harness_cli.py ingest $(NODE)

serve:            ## MCP 서버:  make serve NODE=my_proj
	$(PY) tools/harness_cli.py serve $(NODE)

info:             ## 정보 요약:  make info NODE=my_proj
	$(PY) tools/harness_cli.py info $(NODE)

test:             ## 스모크 테스트
	HARNESS_EMBED_BACKEND=hash bash scripts/smoke_test.sh

clean:            ## 파생물/캐시 정리 (info/ 는 재생성 가능)
	find . -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
