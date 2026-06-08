#!/usr/bin/env python3
"""bootstrap — 노드 manifest를 읽어 repo 링크 + 의존성을 멱등하게 셋업.

지원 link.type: path | git-submodule | git-clone | symlink  (ARCHITECTURE §4)
"""
from __future__ import annotations
import argparse, os, subprocess, sys

__tool_version__ = "0.1.0"

def load_manifest(node_dir: str) -> dict:
    p = os.path.join(node_dir, "manifest.yaml")
    try:
        import yaml
        return yaml.safe_load(open(p))
    except ImportError:
        print("[bootstrap] PyYAML 필요: pip install pyyaml", file=sys.stderr); sys.exit(2)

def sh(cmd, cwd=None, dry=False):
    print(f"  $ {cmd}" + (f"  (cwd={cwd})" if cwd else ""))
    if dry:
        return 0
    return subprocess.call(cmd, shell=True, cwd=cwd)

def link_repo(node_dir: str, link: dict, dry: bool):
    path = os.path.join(node_dir, link.get("path", "repo"))
    t = link["type"]
    if t == "path":
        os.makedirs(path, exist_ok=True)
        print(f"[bootstrap] link=path — {path} 사용(외부 VCS 없음)")
    elif t == "git-clone":
        if os.path.exists(os.path.join(path, ".git")):
            print(f"[bootstrap] 이미 clone됨 — fetch만"); sh(f"git -C {path} fetch", dry=dry)
        else:
            sh(f"git clone {link['url']} {path}", dry=dry)
        if link.get("ref"):
            sh(f"git -C {path} checkout {link['ref']}", dry=dry)
    elif t == "git-submodule":
        sh(f"git submodule update --init -- {path}", cwd=node_dir, dry=dry)
    elif t == "symlink":
        target = link.get("target")
        if not target:
            print("[bootstrap] link=symlink 에는 manifest 의 link.target 이 필요합니다.", file=sys.stderr); sys.exit(2)
        # 상대경로는 노드 디렉토리 기준으로 해석 후 절대경로화 (WSL 네이티브 FS 권장)
        target_abs = target if os.path.isabs(target) else os.path.normpath(os.path.join(node_dir, target))
        if not os.path.isdir(target_abs):
            print(f"[bootstrap] symlink 대상 디렉토리가 없습니다: {target_abs}", file=sys.stderr); sys.exit(2)
        if os.path.islink(path):
            if os.path.realpath(path) == os.path.realpath(target_abs):
                print(f"[bootstrap] link=symlink — {path} → {target_abs} (이미 연결됨)"); return path
            print(f"[bootstrap] link=symlink — 기존 심링크 교체 → {target_abs}")
            if not dry: os.unlink(path)
        elif os.path.isdir(path):
            if os.listdir(path):
                print(f"[bootstrap] {path} 가 비어있지 않은 디렉토리입니다. 수동 정리 후 재시도하세요.", file=sys.stderr); sys.exit(2)
            if not dry: os.rmdir(path)   # 템플릿이 만든 빈 repo/ 제거 후 심링크 대체
        elif os.path.exists(path):
            print(f"[bootstrap] {path} 가 파일로 존재합니다. 수동 정리 필요.", file=sys.stderr); sys.exit(2)
        print(f"[bootstrap] link=symlink — {path} → {target_abs}")
        if not dry: os.symlink(target_abs, path)
    else:
        print(f"[bootstrap] unknown link.type: {t}", file=sys.stderr); sys.exit(2)
    return path

def install_deps(repo_path: str, boot: dict, dry: bool):
    for cmd in boot.get("setup", []):
        sh(cmd, cwd=repo_path, dry=dry)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--node", required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    m = load_manifest(a.node)
    print(f"[bootstrap] node={m['node']['name']} schema_v{m['node']['schema_version']}")
    repo = link_repo(a.node, m["link"], a.dry_run)
    install_deps(repo, m.get("bootstrap", {}), a.dry_run)
    print("[bootstrap] done.")

if __name__ == "__main__":
    main()
