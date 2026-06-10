#!/usr/bin/env bash
# ai-autodev-harness 셋업 (Linux / WSL 우선). 멱등.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> 환경 확인"
grep -qiE "(microsoft|wsl)" /proc/version 2>/dev/null && echo "    WSL 감지됨" || echo "    Linux"
command -v python3 >/dev/null || { echo "python3 필요"; exit 1; }

echo "==> 시스템 패키지 (OCR용 tesseract)"
if ! command -v tesseract >/dev/null; then
  if command -v apt-get >/dev/null; then
    echo "    sudo apt-get install -y tesseract-ocr (이미지 OCR 사용 시)"
    sudo apt-get update -y && sudo apt-get install -y tesseract-ocr || echo "    [경고] tesseract 설치 실패 — 이미지 인제스트만 영향"
  else
    echo "    [안내] tesseract 미설치. 패키지 매니저로 설치하세요(이미지 OCR 사용 시)."
  fi
else
  echo "    tesseract OK: $(tesseract --version 2>&1 | head -1)"
fi

echo "==> Python venv (.venv)"
[ -d .venv ] || python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install -U pip wheel >/dev/null
echo "==> 의존성 설치 (requirements.txt)"
pip install -r requirements.txt

echo "==> .env"
[ -f .env ] || { cp .env.example .env; echo "    .env 생성 — ANTHROPIC_API_KEY 를 채우세요"; }

echo "==> 검증"
python - <<'PY'
import mcp, sqlite_vec, sqlite3
c=sqlite3.connect(":memory:"); c.enable_load_extension(True); sqlite_vec.load(c)
print("    sqlite-vec:", c.execute("select vec_version()").fetchone()[0], "| mcp import OK")
PY
echo
echo "완료. 사용:  ./harness init my_proj   (자세히: docs/USAGE.md)"
echo "참고: 기본 임베딩 Qwen3-Embedding-0.6B(~1.2GB) 최초 1회 다운로드(대안 BAAI/bge-m3). 오프라인/테스트는 HARNESS_EMBED_BACKEND=hash."
