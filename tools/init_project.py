#!/usr/bin/env python3
"""init_project — _template-node 를 복제해 새 프로젝트 노드를 생성.

projects/<name>-node/ 생성 → manifest 치환 → ONBOARDING 치환 → 다음 단계 안내.
멱등: 이미 있으면 거부(--force 로 덮어쓰기).
"""
from __future__ import annotations
import argparse
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # tools/ 의 부모 = 플랫폼 루트
TEMPLATE = os.path.join(ROOT, "projects", "_template-node")


def _sub_in_file(path, repl: dict):
    if not os.path.exists(path):
        return
    s = open(path, encoding="utf-8").read()
    for k, v in repl.items():
        s = s.replace(k, v)
    open(path, "w", encoding="utf-8").write(s)


_PRIVATE_GITIGNORE = (
    "# Private node — never commit data, originals, or derived info (confidential / regenerable).\n"
    "archives/\n"
    "info/\n"
    "data/update/*\n"
    "!data/update/.gitkeep\n"
)


def init(name, link_type, url, ref, force, target=None, private=False):
    if not os.path.isdir(TEMPLATE):
        print("[init] 템플릿 없음: %s" % TEMPLATE, file=sys.stderr); return 1
    dest = os.path.join(ROOT, "projects", "%s-node" % name)
    if os.path.exists(dest):
        if not force:
            print("[init] 이미 존재: %s (--force 로 덮어쓰기)" % dest, file=sys.stderr); return 1
        shutil.rmtree(dest)
    shutil.copytree(TEMPLATE, dest)

    man = os.path.join(dest, "manifest.yaml")
    repl = {"REPLACE_ME": name}
    _sub_in_file(man, repl)
    # link 설정 갱신
    s = open(man, encoding="utf-8").read()
    s = s.replace("type: git-clone", "type: %s" % link_type)
    if url:
        s = s.replace("git@github.com:org/%s.git" % name, url)
    if ref:
        s = s.replace("ref: main", "ref: %s" % ref)
    if link_type == "symlink" and target:
        s = s.replace("  path: repo", "  path: repo\n  target: %s" % target)
    if private:
        # Mark the node private; data/originals/derived info stay local (see node .gitignore below).
        s = s.replace("node:\n", "node:\n  private: true\n", 1)
    open(man, "w", encoding="utf-8").write(s)
    if private:
        open(os.path.join(dest, ".gitignore"), "w", encoding="utf-8").write(_PRIVATE_GITIGNORE)
    _sub_in_file(os.path.join(dest, "history", "ONBOARDING.md"), repl)
    # Always ensure repo/ exists — it is where THIS project's code lives (zero-base or linked).
    # (Empty dirs aren't carried by git, so a clone's template may lack it.)
    os.makedirs(os.path.join(dest, "repo"), exist_ok=True)

    rel = os.path.relpath(dest, ROOT)
    print("[init] 생성 완료: %s" % rel)
    print("     코드는 %s/repo/ 안에서만 작성한다(플랫폼 루트/현재 디렉토리 금지)." % rel)
    print("\n다음 단계:")
    if link_type == "path":
        print("  1) (제로베이스) 코드를 %s/repo/ 에 바로 작성 — 새 git 으로 관리하려면 그 안에서 git init" % rel)
    else:
        print("  1) repo 링크/의존성:  python tools/bootstrap/install.py --node %s" % rel)
    print("  2) 데이터 인제스트:    %s/data/update/ 에 파일 투입 후" % rel)
    print("                         python tools/data-to-info/router.py --node %s" % rel)
    print("  3) (선택) 하네스 활성화: platform/harnesses.yaml + harness gen-rules / sync-skills")
    print("  4) MCP 서버 등록:      adapters/mcp.example.json 참고 (NODE_DIR=%s)" % rel)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name", help="프로젝트 이름 (예: my_proj)")
    ap.add_argument("--link-type", default="path", choices=["path", "git-submodule", "git-clone", "symlink"])
    ap.add_argument("--url", default=None, help="git-clone/submodule 의 원격 URL")
    ap.add_argument("--ref", default=None, help="브랜치/태그/커밋")
    ap.add_argument("--target", default=None, help="link-type=symlink 의 대상 디렉토리(절대경로 권장)")
    ap.add_argument("--private", action="store_true", help="기밀 노드: 데이터/산출물 미추적")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    sys.exit(init(a.name, a.link_type, a.url, a.ref, a.force, a.target, a.private))


if __name__ == "__main__":
    main()
