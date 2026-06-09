#!/usr/bin/env bash
# post_clone — git clone 후 1회 실행하면 바로 사용 가능 상태로 만든다(멱등).
# 클론에 빠지는 것만 복구: (1).venv+의존성 (2)git 훅 (3)진입규칙 심링크 (4)벡터 스토어.
# 소스/문서/정본 AGENTS.md/스킬/archives/md/sql/index 는 git 으로 이미 따라온다.
# 사용:  bash scripts/post_clone.sh   (또는: make ready)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"

echo "==> [1/4] 환경 셋업 (venv + 의존성 + tesseract 안내)"
bash scripts/setup.sh

PY=.venv/bin/python
echo "==> [2/4] git pre-commit 훅 설치"
if [ -d .git ]; then
  "$PY" tools/install_hooks.py || true
else
  echo "    (git 저장소 아님 — 'git init' 후 다시 실행하면 훅 설치)"
fi

shopt -s nullglob
echo "==> [3/4] 진입 규칙 심링크 생성 (정본 AGENTS.md → CLAUDE/GEMINI/.cursorrules/Copilot)"
"$PY" tools/gen_agent_rules.py >/dev/null || true
for nd in projects/*-node; do
  base="$(basename "$nd")"
  [ "$base" = "_template-node" ] && continue
  [ -f "$nd/manifest.yaml" ] || continue
  "$PY" tools/gen_agent_rules.py --node "${base%-node}" >/dev/null || true
done

echo "==> [4/4] 노드 벡터 스토어 재생성 (없을 때만; backend=${HARNESS_EMBED_BACKEND:-local})"
for nd in projects/*-node; do
  base="$(basename "$nd")"
  [ "$base" = "_template-node" ] && continue
  [ -f "$nd/manifest.yaml" ] || continue
  if [ -f "$nd/info/vector/store.db" ]; then
    echo "    skip (이미 있음): $nd"
  else
    echo "    rebuild: $nd"
    "$PY" tools/harness_cli.py rebuild "$nd" || echo "    [건너뜀] $nd (archives 없음/의존성 문제)"
  fi
done

echo "==> 준비 완료.  source .venv/bin/activate  후  ./harness <명령> 사용."
echo "    (오프라인/모델다운로드 회피:  HARNESS_EMBED_BACKEND=hash make ready)"
