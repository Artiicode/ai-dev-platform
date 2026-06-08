#!/usr/bin/env python3
"""harness — ai-autodev-harness 통합 CLI (Linux/WSL 우선).

서브커맨드:
  init       새 프로젝트 노드 생성 (_template-node 복제)
  bootstrap  manifest 기반 repo 링크 + 의존성 설치
  ingest     data/update/* -> info/ (md/sql/vector) 적재
  serve      해당 노드의 MCP 서버 실행 (stdio 기본, sse 가능)
  info       노드의 정보 자산 요약 (md/sql/vector)
  search     벡터 RAG 시맨틱 검색
  query      info/db 읽기 전용 SQL
  onboard    history/* 스캔해 ONBOARDING.md 재생성
  debug      scenario/debug 플레이북 구동 (dry-run 기본, --execute 시 락+승인)
  lock       노드 advisory 락 획득/상태
  unlock     노드 락 해제
  worktree   ticket용 git worktree 생성

노드 인자는 이름(project_A) 또는 경로(projects/project_A-node) 둘 다 허용.
"""
from __future__ import annotations
import argparse
import getpass
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in ("tools", "tools/lib", "tools/data-to-info", "tools/bootstrap", "mcp"):
    sys.path.insert(0, os.path.join(ROOT, p))


def resolve_node(arg):
    for c in [arg, os.path.join(ROOT, arg),
              os.path.join(ROOT, "projects", arg + "-node"),
              os.path.join(ROOT, "projects", arg)]:
        if os.path.isdir(c) and os.path.exists(os.path.join(c, "manifest.yaml")):
            return os.path.abspath(c)
    sys.exit("[harness] 노드를 찾을 수 없음: %s (init 먼저?)" % arg)


def cmd_init(a):
    import init_project
    return init_project.init(a.name, a.link_type, a.url, a.ref, a.force, getattr(a, "target", None))


def cmd_genrules(a):
    import gen_agent_rules
    return gen_agent_rules.generate(getattr(a, "node", None))


def cmd_validate(a):
    import validate_node
    nodes = [resolve_node(a.node)] if a.node else None
    return validate_node.validate_all(nodes, strict=a.strict)


def cmd_installhooks(a):
    import install_hooks
    return install_hooks.main()


def cmd_models(a):
    import llm
    return llm.audit()


def cmd_bootstrap(a):
    import install
    node = resolve_node(a.node); m = install.load_manifest(node)
    repo = install.link_repo(node, m["link"], a.dry_run)
    install.install_deps(repo, m.get("bootstrap", {}), a.dry_run)
    print("[harness] bootstrap done."); return 0


def cmd_ingest(a):
    import router
    return router.run(resolve_node(a.node), a.md_max, a.vector_min, a.dry_run)


def cmd_serve(a):
    node = resolve_node(a.node)
    os.environ["NODE_DIR"] = node
    if a.transport:
        os.environ["HARNESS_MCP_TRANSPORT"] = a.transport
    import server
    server.mcp.run(transport=os.environ.get("HARNESS_MCP_TRANSPORT", "stdio"))
    return 0


def _server_for(node):
    os.environ["NODE_DIR"] = resolve_node(node)
    import importlib, server
    importlib.reload(server)
    return server


def cmd_info(a):
    import json
    print(json.dumps(_server_for(a.node).list_info(), ensure_ascii=False, indent=2)); return 0


def cmd_search(a):
    hits = _server_for(a.node).search_info(a.query, a.k)
    for h in hits:
        if "error" in h:
            print("[error]", h["error"]); return 1
        print("%-26s dist=%.3f  %s" % (h["doc_id"], h["distance"], h["text"][:80].replace("\n", " ").strip()))
    return 0


def cmd_query(a):
    import json
    print(json.dumps(_server_for(a.node).query_sql(a.sql, a.db), ensure_ascii=False, indent=2)); return 0


def cmd_onboard(a):
    import gen_onboarding
    out, na, nadr = gen_onboarding.generate(resolve_node(a.node))
    print("[onboard] 생성: %s (활성 티켓 %d, ADR %d)" % (out, na, nadr)); return 0


def cmd_debug(a):
    import debug_runner
    return debug_runner.run(resolve_node(a.node), a.ticket, a.name, a.target,
                            a.build, a.run_cmd, a.execute)


def cmd_lock(a):
    import locks
    node = resolve_node(a.node)
    if a.status:
        cur = locks.read(node)
        print(cur if cur else "(락 없음)"); return 0
    owner = a.owner or ("cli:%s" % getpass.getuser())
    try:
        info = locks.acquire(node, owner, ticket=a.ticket)
        print("[lock] 획득: owner=%s ticket=%s" % (info["owner"], info["ticket"])); return 0
    except locks.LockError as e:
        print("[lock] 실패: %s" % e, file=sys.stderr); return 1


def cmd_unlock(a):
    import locks
    owner = a.owner or ("cli:%s" % getpass.getuser())
    try:
        ok = locks.release(resolve_node(a.node), owner)
        print("[unlock] %s" % ("해제됨" if ok else "락 없음")); return 0
    except locks.LockError as e:
        print("[unlock] 실패: %s" % e, file=sys.stderr); return 1


def cmd_worktree(a):
    import worktree
    node = resolve_node(a.node)
    repo = os.path.join(node, "repo")
    branch = a.branch or ("%s-work" % a.ticket)
    wt = a.path or os.path.join(node, "state", "wt-%s" % branch)
    res = worktree.create(repo, branch, wt, base=a.base, dry=a.dry_run)
    print("[worktree] %s" % (res or "no-op")); return 0



def cmd_rebuild(a):
    import rebuild
    return rebuild.rebuild(resolve_node(a.node), a.md_max, a.vector_min)


def cmd_verify(a):
    import verify
    return verify.run(resolve_node(a.node))


def cmd_webgui(a):
    import subprocess
    node = resolve_node(a.node)
    env = dict(os.environ, NODE_DIR=node)
    srv = os.path.join(ROOT, "adapters", "web-gui", "server.py")
    return subprocess.call([sys.executable, srv, "--port", str(a.port), "--host", a.host], env=env)


def build_parser():
    ap = argparse.ArgumentParser(prog="harness", description="ai-autodev-harness CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init"); p.add_argument("name")
    p.add_argument("--link-type", default="path", choices=["path", "git-submodule", "git-clone", "symlink"])
    p.add_argument("--url"); p.add_argument("--ref"); p.add_argument("--force", action="store_true")
    p.add_argument("--target", help="link-type=symlink 의 대상 디렉토리(절대경로 권장)")
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("gen-rules"); p.add_argument("--node", default=None)
    p.set_defaults(fn=cmd_genrules)

    p = sub.add_parser("validate"); p.add_argument("node", nargs="?", default=None)
    p.add_argument("--strict", action="store_true", help="경고도 실패로 처리")
    p.set_defaults(fn=cmd_validate)

    p = sub.add_parser("install-hooks"); p.set_defaults(fn=cmd_installhooks)

    p = sub.add_parser("models"); p.set_defaults(fn=cmd_models)

    p = sub.add_parser("bootstrap"); p.add_argument("node"); p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_bootstrap)

    p = sub.add_parser("ingest"); p.add_argument("node")
    p.add_argument("--md-max", type=int, default=8000); p.add_argument("--vector-min", type=int, default=8000)
    p.add_argument("--dry-run", action="store_true"); p.set_defaults(fn=cmd_ingest)

    p = sub.add_parser("serve"); p.add_argument("node")
    p.add_argument("--transport", choices=["stdio", "sse", "streamable-http"], default=None)
    p.set_defaults(fn=cmd_serve)

    p = sub.add_parser("info"); p.add_argument("node"); p.set_defaults(fn=cmd_info)

    p = sub.add_parser("search"); p.add_argument("node"); p.add_argument("query")
    p.add_argument("-k", type=int, default=5); p.set_defaults(fn=cmd_search)

    p = sub.add_parser("query"); p.add_argument("node"); p.add_argument("sql")
    p.add_argument("--db", default=None); p.set_defaults(fn=cmd_query)

    p = sub.add_parser("onboard"); p.add_argument("node"); p.set_defaults(fn=cmd_onboard)

    p = sub.add_parser("debug"); p.add_argument("node")
    p.add_argument("--ticket", required=True); p.add_argument("--name", required=True)
    p.add_argument("--target", default="jetson_agx_orin"); p.add_argument("--build", default=None)
    p.add_argument("--run-cmd", default=None); p.add_argument("--execute", action="store_true")
    p.set_defaults(fn=cmd_debug)

    p = sub.add_parser("lock"); p.add_argument("node"); p.add_argument("--ticket", default=None)
    p.add_argument("--owner", default=None); p.add_argument("--status", action="store_true")
    p.set_defaults(fn=cmd_lock)

    p = sub.add_parser("unlock"); p.add_argument("node"); p.add_argument("--owner", default=None)
    p.set_defaults(fn=cmd_unlock)

    p = sub.add_parser("worktree"); p.add_argument("node"); p.add_argument("--ticket", required=True)
    p.add_argument("--branch", default=None); p.add_argument("--path", default=None)
    p.add_argument("--base", default="HEAD"); p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_worktree)
    p = sub.add_parser("rebuild"); p.add_argument("node")
    p.add_argument("--md-max", type=int, default=8000); p.add_argument("--vector-min", type=int, default=8000)
    p.set_defaults(fn=cmd_rebuild)

    p = sub.add_parser("verify"); p.add_argument("node"); p.set_defaults(fn=cmd_verify)

    p = sub.add_parser("webgui"); p.add_argument("node")
    p.add_argument("--port", type=int, default=8800); p.add_argument("--host", default="127.0.0.1")
    p.set_defaults(fn=cmd_webgui)

    return ap


def main():
    a = build_parser().parse_args()
    sys.exit(a.fn(a))


if __name__ == "__main__":
    main()
