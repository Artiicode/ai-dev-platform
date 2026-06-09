#!/usr/bin/env python3
"""sync_skills — 정본 스킬/커맨드를 활성 하네스의 네이티브 위치로 배포(레지스트리 구동).

핵심 플랫폼은 하네스 중립이다. 스킬/커맨드는 **중립 마크다운 1벌(정본)**로 정의하고,
`platform/harnesses.yaml`의 `enabled` 하네스에 한해 그 하네스 위치로 *투영*한다.
기본은 복제(이식성↑, Windows 안전), `--link` 시 심볼릭 링크(POSIX).

정본(추적):
  - 스킬:   platform/skills/<slug>.md      (노드: projects/<n>-node/skills/<slug>.md)
  - 커맨드: platform/commands/<slug>.md
배포(미추적, 활성 하네스별):
  - <base>/<harness.skills_dir>/<slug>/SKILL.md
  - <base>/<harness.commands_dir>/<slug>.md
사용: python tools/sync_skills.py [--node NAME] [--link]
"""
from __future__ import annotations
import argparse, os, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools", "lib"))
import registry  # platform/harnesses.yaml

SKIP = {"index.md", "readme.md", "_template.md"}


def _defs(src_dir):
    if not os.path.isdir(src_dir):
        return
    for name in sorted(os.listdir(src_dir)):
        if name.endswith(".md") and name.lower() not in SKIP:
            yield name[:-3], os.path.join(src_dir, name)


def _emit(src, dst, use_link):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.islink(dst) or os.path.exists(dst):
        os.remove(dst)
    if use_link:
        os.symlink(os.path.relpath(src, os.path.dirname(dst)), dst)
    else:
        shutil.copyfile(src, dst)


def _project(base_dir, skills_src, commands_src, use_link):
    out = []
    for name, cfg in registry.enabled():
        cfg = cfg or {}
        sdir = cfg.get("skills_dir")
        if sdir:
            for slug, src in _defs(skills_src):
                dst = os.path.join(base_dir, sdir, slug, "SKILL.md")
                _emit(src, dst, use_link); out.append((os.path.relpath(dst, ROOT), name))
        cdir = cfg.get("commands_dir")
        if cdir and commands_src:
            for slug, src in _defs(commands_src):
                dst = os.path.join(base_dir, cdir, slug + ".md")
                _emit(src, dst, use_link); out.append((os.path.relpath(dst, ROOT), name))
    return out


def sync(node: str | None = None, use_link: bool = False):
    if not registry.enabled():
        print("[sync-skills] 활성 하네스 없음(platform/harnesses.yaml `enabled` 비어있음) — 배포 생략.")
        return 0
    written = _project(ROOT, os.path.join(ROOT, "platform", "skills"),
                       os.path.join(ROOT, "platform", "commands"), use_link)
    if node:
        nd = os.path.join(ROOT, "projects", "%s-node" % node)
        if not os.path.isdir(nd):
            print("[sync-skills] 노드 없음: %s" % nd, file=sys.stderr); return 1
        written += _project(nd, os.path.join(nd, "skills"), None, use_link)
    mode = "심링크" if use_link else "복제"
    print("[sync-skills] 배포 %d개 (%s):" % (len(written), mode))
    for path, hn in written:
        print("  - %-50s [%s]" % (path, hn))
    if not written:
        print("  (정본 스킬/커맨드 없음 — platform/skills|commands/<slug>.md 추가)")
    return 0


def main():
    ap = argparse.ArgumentParser(description="정본 스킬/커맨드를 활성 하네스로 배포")
    ap.add_argument("--node", default=None, help="노드 스킬도 배포(예: project_A)")
    ap.add_argument("--link", action="store_true", help="복제 대신 심볼릭 링크(POSIX 전용)")
    a = ap.parse_args()
    sys.exit(sync(a.node, a.link))


if __name__ == "__main__":
    main()
