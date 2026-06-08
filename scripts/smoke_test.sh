#!/usr/bin/env bash
# 격리 임시 복사본에서 전체 파이프라인 스모크 (projects/ 오염 없음).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PY:-python3}"
export HARNESS_EMBED_BACKEND="${HARNESS_EMBED_BACKEND:-hash}"   # 오프라인 기본
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
cp -r "$ROOT/tools" "$ROOT/mcp" "$TMP/"
mkdir -p "$TMP/projects"; cp -r "$ROOT/projects/_template-node" "$TMP/projects/"
cd "$TMP"

echo "== init =="; $PY tools/harness_cli.py init smoke --link-type path >/dev/null
N=projects/smoke-node
echo '{"poses":[{"x":1,"y":2,"z":3,"label":"home"},{"x":7,"y":8,"z":9,"label":"pick"}]}' > $N/data/update/poses.json
printf '# Note\nSmall spec doc.\n' > $N/data/update/note.md
$PY - <<PY
open("$N/data/update/big.txt","w").write(("Jetson AGX Orin deploy over SSH, scp binary to /root. ")*200)
PY

echo "== ingest =="; $PY tools/harness_cli.py ingest $N
echo "== info ==";   $PY tools/harness_cli.py info smoke
echo "== query =="; $PY tools/harness_cli.py query smoke "SELECT label,z FROM poses WHERE z>=5"
echo "== search =="; $PY tools/harness_cli.py search smoke "deploy binary to jetson" -k 2

# 어서션
$PY - <<PY
import os,glob,sqlite3
N="projects/smoke-node"
assert glob.glob(N+"/info/db/*.sqlite"), "sql 적재 실패"
assert os.path.exists(N+"/info/vector/store.db"), "vector 적재 실패"
assert glob.glob(N+"/info/md/*"), "md 적재 실패"
print("\n[PASS] sql + vector + md 적재 + CLI 동작 확인")
PY
