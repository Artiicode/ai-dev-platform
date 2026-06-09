#!/usr/bin/env python3
"""sync_skills — 정본 스킬을 각 AI 하네스의 네이티브 위치로 배포(크로스플랫폼 추상화).

설계 원칙: 특정 stack/플랫폼 의존을 최소화한다. 스킬은 **하네스 중립 마크다운 1벌**(정본)로
정의하고, 어댑터가 각 하네스 위치로 *투영*한다. 기본은 **복제**(이식성↑, Windows 체크아웃 안전).
`--link` 시 심볼릭 링크(POSIX, 단일 원본 유지) — 단 이는 POSIX 의존이므로 선택사항.

정본:
  - 전역: platform/skills/<slug>.md
  - 노드: projects/<name>-node/skills/<slug>.md   (--node <name>)
배포 대상(각 base 아래):
  - .claude/skills/<slug>/SKILL.md     (Claude Code)
  - .cursor/skills/<slug>/SKILL.md     (Cursor)

정본 <slug>.md 는 SKILL.md 규격(상단 frontmatter: name/description) 그대로 두는 것을 권장.
사용: python tools/sync_skills.py [--node NAME] [--link]
"""
from __future__ import annotations
import argparse, os, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP = {"index.md", "readme.md", "_template.md"}
HARNESS_SUBDIRS = (os.path.join(".claude", "skills"), os.path.join(".cursor", "skills"))


def _skill_files(src_dir):
    if not os.path.isdir(src_dir):
        return
    for name in sorted(os.listdir(src_dir)):
        if name.endswith(".md") and name.lower() not in SKIP:
            yield name[:-3], os.path.join(src_dir, name)


def _project(base_dir, src_dir, use_link):
    out = []
    for slug, src in _skill_files(src_dir):
        for sub in HARNESS_SUBDIRS:
            dst_dir = os.path.join(base_dir, sub, slug)
            os.makedirs(dst_dir, exist_ok=True)
            dst = os.path.join(dst_dir, "SKILL.md")
            if os.path.islink(dst) or os.path.exists(dst):
                os.remove(dst)
            if use_link:
                os.symlink(os.path.relpath(src, dst_dir), dst)
            else:
                shutil.copyfile(src, dst)
            out.append(os.path.relpath(dst, ROOT))
    return out


def sync(node: str | None = None, use_link: bool = False):
    written = _project(ROOT, os.path.join(ROOT, "platform", "skills"), use_link)
    print("[sync-skills] 전역 (platform/skills → 루트 .claude/.cursor): %d" % len(written))
    if node:
        nd = os.path.join(ROOT, "projects", "%s-node" % node)
        if not os.path.isdir(nd):
            print("[sync-skills] 노드 없음: %s" % nd, file=sys.stderr); return 1
        wn = _project(nd, os.path.join(nd, "skills"), use_link)
        print("[sync-skills] 노드 %s (skills → 노드 .claude/.cursor): %d" % (node, len(wn)))
        written += wn
    mode = "심링크" if use_link else "복제"
    for w in written:
        print("  - %s (%s)" % (w, mode))
    if not written:
        print("  (정본 스킬 없음 — platform/skills/<slug>.md 를 추가하세요)")
    return 0


def main():
    ap = argparse.ArgumentParser(description="정본 스킬을 하네스별 위치로 배포")
    ap.add_argument("--node", default=None, help="노드 스킬도 배포(예: project_A)")
    ap.add_argument("--link", action="store_true", help="복제 대신 심볼릭 링크(POSIX 전용)")
    a = ap.parse_args()
    sys.exit(sync(a.node, a.link))


if __name__ == "__main__":
    main()
