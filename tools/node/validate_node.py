#!/usr/bin/env python3
"""validate_node — 노드 적합성 검증 (강제성 ① 보편층의 기계적 게이트).

pre-commit / CI 훅이 호출하며, 규칙 위반 산출물을 거부한다. 단독 실행도 가능.
검사 항목:
  1. manifest.yaml 이 node-manifest 스키마를 만족 (jsonschema; B2 해소)
  2. info/index.yaml 이 info-index 스키마를 만족(있을 때)
  3. 필수 노드 디렉토리/파일 존재 (구조 규칙)
  4. history/ONBOARDING.md 존재 (인계 규칙)
  5. repo/ 청결 — AI 메타 파일이 코드 repo 안에 들어가지 않았는지 (파일 배치 규칙)
  6. 평문 시크릿 미포함 (platform/policies/secrets.md)
  7. link.type=symlink 의 target 유효성

종료코드: 에러 있으면 1, 없으면 0. --strict 시 경고도 1.

사용:
  python tools/validate_node.py                # 모든 projects/*-node (템플릿 제외)
  python tools/validate_node.py <node_dir>     # 특정 노드
"""
from __future__ import annotations
import glob, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCHEMA_DIR = os.path.join(ROOT, "docs", "schemas")

REQUIRED_DIRS = ["data/update", "info", "archives", "code", "scenario", "history", "hw"]
REQUIRED_FILES = ["manifest.yaml", "history/ONBOARDING.md"]
# repo/ 안에 있으면 안 되는 AI 메타 흔적 (배치 규칙 위반)
REPO_FORBIDDEN = ["manifest.yaml", "history", "scenario", "info/index.yaml",
                  "code/coding_convention", "ONBOARDING.md"]
# 평문 시크릿 패턴
SECRET_PATTERNS = [
    (re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"), "개인키"),
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"), "OpenAI 형식 키"),
    (re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}\b"), "Anthropic 키"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS 액세스키"),
    (re.compile(r"(?i)\b(password|passwd|secret|api[_-]?key)\s*[:=]\s*['\"]?[^\s'\"#]{6,}"), "평문 비밀값"),
]
# 시크릿 스캔에서 제외할 텍스트(예시/플레이스홀더)
SECRET_ALLOW = re.compile(r"(REPLACE_ME|<[^>]+>|example|placeholder|\$\{|_env|채우세요|xxx+|\.\.\.)", re.I)
SCAN_SKIP_DIRS = {"repo", "archives", ".git", "info"}  # info: 벡터 DB 등 바이너리
SCAN_EXT = {".md", ".yaml", ".yml", ".json", ".txt", ".cfg", ".ini", ".env"}


def _load_yaml(path):
    import yaml
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _validate_schema(instance, schema_path, errors, label):
    if not os.path.exists(schema_path):
        return
    try:
        import jsonschema, json
    except ImportError:
        return  # jsonschema 미설치 → 스키마 검증 생략(경고는 호출부에서)
    schema = json.load(open(schema_path, encoding="utf-8"))
    v = jsonschema.Draft202012Validator(schema)
    for e in sorted(v.iter_errors(instance), key=lambda x: list(x.path)):
        loc = "/".join(str(p) for p in e.path) or "(root)"
        errors.append("%s 스키마 위반 [%s]: %s" % (label, loc, e.message))


def _walk_text_files(node_dir):
    for dp, dns, fns in os.walk(node_dir):
        dns[:] = [d for d in dns if d not in SCAN_SKIP_DIRS]
        for fn in fns:
            if os.path.splitext(fn)[1].lower() in SCAN_EXT or fn == ".env":
                yield os.path.join(dp, fn)


def validate_node(node_dir, strict=False):
    """단일 노드 검증. (errors, warnings) 반환."""
    errors, warnings = [], []
    name = os.path.basename(node_dir.rstrip("/"))

    # 1. manifest 스키마
    man_path = os.path.join(node_dir, "manifest.yaml")
    manifest = None
    if not os.path.exists(man_path):
        errors.append("manifest.yaml 없음")
    else:
        try:
            manifest = _load_yaml(man_path)
            _validate_schema(manifest, os.path.join(SCHEMA_DIR, "node-manifest.schema.json"),
                             errors, "manifest")
        except Exception as e:
            errors.append("manifest.yaml 파싱 실패: %s" % e)

    # jsonschema 가용성 경고(1회)
    try:
        import jsonschema  # noqa: F401
    except ImportError:
        warnings.append("jsonschema 미설치 — 스키마 검증 생략(pip install jsonschema 권장)")

    # 2. info/index.yaml 스키마
    idx = os.path.join(node_dir, "info", "index.yaml")
    if os.path.exists(idx):
        try:
            _validate_schema(_load_yaml(idx), os.path.join(SCHEMA_DIR, "info-index.schema.json"),
                             errors, "info/index.yaml")
        except Exception as e:
            errors.append("info/index.yaml 파싱 실패: %s" % e)

    # 3~4. 구조/필수파일
    for d in REQUIRED_DIRS:
        if not os.path.isdir(os.path.join(node_dir, d)):
            errors.append("필수 디렉토리 없음: %s/" % d)
    for f in REQUIRED_FILES:
        if not os.path.exists(os.path.join(node_dir, f)):
            errors.append("필수 파일 없음: %s" % f)

    # 5. repo/ 청결 (심링크면 대상 코드이므로 검사 생략)
    repo = os.path.join(node_dir, "repo")
    if os.path.isdir(repo) and not os.path.islink(repo):
        for forb in REPO_FORBIDDEN:
            if os.path.exists(os.path.join(repo, forb)):
                errors.append("repo/ 안에 AI 메타가 있음(배치 규칙 위반): repo/%s" % forb)

    # 6. 평문 시크릿
    for fp in _walk_text_files(node_dir):
        try:
            txt = open(fp, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        for ln in txt.splitlines():
            if SECRET_ALLOW.search(ln):
                continue
            for pat, desc in SECRET_PATTERNS:
                if pat.search(ln):
                    rel = os.path.relpath(fp, node_dir)
                    errors.append("평문 시크릿 의심(%s): %s" % (desc, rel))
                    break

    # 7. symlink target
    if manifest and isinstance(manifest, dict):
        link = manifest.get("link", {}) or {}
        if link.get("type") == "symlink":
            tgt = link.get("target")
            if not tgt:
                errors.append("link.type=symlink 인데 target 없음")
            else:
                tgt_abs = tgt if os.path.isabs(tgt) else os.path.normpath(os.path.join(node_dir, tgt))
                if not os.path.isdir(tgt_abs):
                    warnings.append("symlink target 미존재: %s (bootstrap 전이면 정상)" % tgt_abs)

    # 8a. node metadata git — the node owns its history; repo/ (external code) must NOT leak in.
    try:
        import node_git
        if node_git.is_repo(node_dir):
            if node_git.repo_tracked(node_dir):
                errors.append("repo/ 가 노드 git 에 추적됨 — 외부 코드가 노드 이력에 흡수됨"
                              "(.gitignore 의 `/repo` 확인; repo 는 자체 repo 에서 관리)")
        else:
            warnings.append("노드 git 미초기화 — `harness bootstrap %s` 또는 ingest/onboard 시 자동 생성됨"
                            % name)
    except Exception:
        pass

    # 8. private node: data / originals / derived info must not be git-tracked
    if manifest and isinstance(manifest, dict) and (manifest.get("node", {}) or {}).get("private"):
        import subprocess
        rels = [os.path.join(os.path.relpath(node_dir, ROOT), d)
                for d in ("archives", "info", "data/update")]
        try:
            out = subprocess.run(["git", "-C", ROOT, "ls-files", "--"] + rels,
                                  capture_output=True, text=True, timeout=10).stdout.split()
        except Exception:
            out = []
        leaked = [p for p in out if not p.endswith(".gitkeep")]
        if leaked:
            errors.append("private 노드인데 데이터가 git 추적됨(%d) — 커밋 금지: %s …"
                          % (len(leaked), ", ".join(leaked[:3])))

    return errors, warnings


def validate_all(nodes=None, strict=False):
    if nodes is None:
        nodes = [d for d in glob.glob(os.path.join(ROOT, "projects", "*-node"))
                 if os.path.basename(d) != "_template-node"]
    if not nodes:
        print("[validate] 검증할 노드 없음."); return 0
    total_err = 0
    for nd in nodes:
        errs, warns = validate_node(nd, strict)
        name = os.path.relpath(nd, ROOT)
        if not errs and not warns:
            print("[validate] OK  %s" % name)
        else:
            print("[validate] %s" % name)
            for e in errs:
                print("   ✗ %s" % e)
            for w in warns:
                print("   ⚠ %s" % w)
        total_err += len(errs) + (len(warns) if strict else 0)
    return 1 if total_err else 0


def main():
    import argparse
    ap = argparse.ArgumentParser(description="노드 적합성 검증(강제성 게이트)")
    ap.add_argument("node", nargs="?", default=None, help="노드 경로(생략 시 전체)")
    ap.add_argument("--strict", action="store_true", help="경고도 실패로 처리")
    a = ap.parse_args()
    nodes = None
    if a.node:
        nd = a.node if os.path.isdir(a.node) else os.path.join(ROOT, "projects", a.node + "-node")
        nodes = [os.path.abspath(nd)]
    sys.exit(validate_all(nodes, a.strict))


if __name__ == "__main__":
    main()
