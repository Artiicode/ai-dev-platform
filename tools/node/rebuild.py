#!/usr/bin/env python3
"""rebuild — info/ 파생물을 archives/(진실 원본)로부터 완전 재생성.

"info 는 파생물, archives 가 진실 원본" 원칙의 실증(ARCHITECTURE 원칙 2).
절차: info/{md,db,vector} 비우기 + index.yaml 리셋 → archives/* 를 data/update 로 복사 → router 재실행.
멱등하며, 스키마/청크 방식이 바뀌어도 동일 입력으로 재구축 가능.
"""
from __future__ import annotations
import argparse
import glob
import os
import shutil
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # tools/node/ → 루트
sys.path.insert(0, os.path.join(_ROOT, "tools", "lib"))
sys.path.insert(0, os.path.join(_ROOT, "tools", "data-to-info"))
import router  # noqa


def _clear_info(node_dir):
    info = os.path.join(node_dir, "info")
    for sub in ("md", "db", "vector"):
        d = os.path.join(info, sub)
        for f in glob.glob(os.path.join(d, "*")):
            if os.path.basename(f) == ".gitkeep":
                continue
            (shutil.rmtree if os.path.isdir(f) else os.remove)(f)
    open(os.path.join(info, "index.yaml"), "w", encoding="utf-8").write(
        "# 파생 정보 인덱스 — rebuild 로 재생성됨\nschema_version: 1\nentries: []\n")


def rebuild(node_dir, md_max, vector_min):
    arch = os.path.join(node_dir, "archives")
    sources = [f for f in glob.glob(os.path.join(arch, "*")) if os.path.isfile(f)]
    if not sources:
        print("[rebuild] archives 비어있음 — 재생성할 원본 없음"); return 0
    print("[rebuild] info/ 초기화 후 archives %d개에서 재생성" % len(sources))
    _clear_info(node_dir)
    inbox = os.path.join(node_dir, "data", "update")
    os.makedirs(inbox, exist_ok=True)
    for s in sources:
        shutil.copy2(s, os.path.join(inbox, os.path.basename(s)))
    # router 가 다시 처리하고 archives 로 (재)이동 → 결과적으로 archives 유지
    return router.run(node_dir, md_max, vector_min, dry_run=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--node", required=True)
    ap.add_argument("--md-max", type=int, default=8000)
    ap.add_argument("--vector-min", type=int, default=8000)
    a = ap.parse_args()
    sys.exit(rebuild(a.node, a.md_max, a.vector_min))


if __name__ == "__main__":
    main()
