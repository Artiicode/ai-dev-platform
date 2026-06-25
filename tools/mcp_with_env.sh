#!/usr/bin/env bash
# mcp_with_env — gitignored 시크릿 파일을 로드한 뒤 실제 MCP 서버를 exec.
# 하네스/셸이 ${VAR} 를 확장하지 않아도, spawn 되는 MCP 프로세스가 시크릿을 환경으로 상속한다.
# 시크릿 값은 추적되지 않는 .env.mcp 에만 존재한다(레지스트리/생성설정엔 평문 금지).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${HARNESS_MCP_ENV:-$ROOT/.env.mcp}"
if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
fi
exec "$@"
