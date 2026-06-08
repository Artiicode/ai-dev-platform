#!/usr/bin/env python3
"""install_hooks — tools/hooks/* 를 .git/hooks/ 에 설치 (강제성 ① 로컬 게이트).

git 저장소가 아니면 안내만 한다(CI 검증은 .github/workflows/validate.yml 가 담당).
"""
from __future__ import annotations
import os, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    git_dir = os.path.join(ROOT, ".git")
    if not os.path.isdir(git_dir):
        print("[install-hooks] git 저장소가 아닙니다. 'git init' 후 다시 실행하세요.")
        print("                (원격/CI 검증은 .github/workflows/validate.yml 로 항상 동작)")
        return 1
    src_dir = os.path.join(ROOT, "tools", "hooks")
    dst_dir = os.path.join(git_dir, "hooks")
    os.makedirs(dst_dir, exist_ok=True)
    n = 0
    for h in sorted(os.listdir(src_dir)):
        src = os.path.join(src_dir, h)
        if not os.path.isfile(src):
            continue
        dst = os.path.join(dst_dir, h)
        shutil.copyfile(src, dst)
        os.chmod(dst, 0o755)
        print("[install-hooks] 설치: .git/hooks/%s" % h)
        n += 1
    print("[install-hooks] 완료 (%d개)." % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
