#!/usr/bin/env python3
"""harness — ai-autodev-harness 통합 CLI (Linux/WSL 우선).

서브커맨드:
  init       새 프로젝트 노드 생성 (_template-node 복제)
  bootstrap  manifest 기반 repo 링크 + 의존성 설치
  ingest     data/update/* -> info/ (md/sql/vector) 적재
  update     플랫폼 업데이트 받기 (git pull --ff-only + 의존성/훅/진입규칙 갱신)
  use        하네스 동적 주입 (enabled 추가 + 진입규칙/스킬 생성): harness use cursor
  mcp        MCP 와이어링 (substrate + 외부 MCP jira/figma 등 → 하네스 설정 병합)
  tool       toolkit 번들 도구 실행 (harness tool <name> -- <args>)
  start      작업 세션 시작 (하네스 선택/기본값 + tmux: 좌 claude/우상 치트시트+셸/우하 usage)
  standup    일 단위 스탠드업 로그 (진행사항/요약) 관리
  serve      해당 노드의 MCP 서버 실행 (stdio 기본, sse 가능)
  info       노드의 정보 자산 요약 (md/sql/vector)
  search     벡터 RAG 시맨틱 검색
  query      info/db 읽기 전용 SQL
  onboard    history/* 스캔해 ONBOARDING.md 재생성
  debug      scenario/debug 플레이북 구동 (dry-run 기본, --execute 시 락+승인)
  lock       노드 advisory 락 획득/상태
  unlock     노드 락 해제
  worktree   ticket용 git worktree 생성

노드 인자는 이름(my_proj) 또는 경로(projects/my_proj-node) 둘 다 허용.
"""
from __future__ import annotations
import argparse
import getpass
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in ("tools", "tools/node", "tools/harness", "tools/lib", "tools/data-to-info",
          "tools/bootstrap", "mcp"):
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
    return init_project.init(a.name, a.link_type, a.url, a.ref, a.force,
                            getattr(a, "target", None), getattr(a, "private", False))


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


def _update_refresh():
    """Refresh derived bits after a successful update: deps + git hooks + entry rules."""
    import subprocess
    req = os.path.join(ROOT, "requirements.txt")
    pip = os.path.join(ROOT, ".venv", "bin", "pip")
    if os.path.exists(pip) and os.path.exists(req):
        subprocess.call([pip, "install", "-q", "-r", req])
    import install_hooks, gen_agent_rules
    install_hooks.main()
    gen_agent_rules.generate()
    print("[update] deps/hooks/entry-rules refreshed. Run 'make ready' to rebuild vectors if data changed.")


def cmd_update(a):
    """Apply platform updates. Fast-forward when possible; otherwise merge and, on conflict,
    surface the exact conflicted files so the agent can resolve them (see AGENTS.md §5).

    The upstream patch MUST land: a clean tree is merged with upstream; only genuinely
    conflicting hunks are left with markers for resolution — never silently dropped.
    """
    import subprocess

    def git(*args, **kw):
        return subprocess.run(["git", "-C", ROOT, *args], **kw)

    print("[update] git fetch")
    if git("fetch", "--all", "--prune").returncode != 0:
        sys.stderr.write("[update] fetch 실패 — 네트워크/원격(origin) 확인.\n")
        return 1
    up = (git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}",
              capture_output=True, text=True).stdout.strip() or "origin/master")

    # 0) Unrelated histories — no common ancestor with upstream. Happens when upstream history
    #    was rewritten (force-push) or the remote was replaced. A normal merge would refuse or
    #    explode in conflicts, so detect it and guide (or resync with --resync).
    if not git("merge-base", "HEAD", up, capture_output=True, text=True).stdout.strip():
        dirty = git("status", "--porcelain", capture_output=True, text=True).stdout.strip()
        ahead = git("rev-list", "--count", "HEAD", "^" + up,
                    capture_output=True, text=True).stdout.strip() or "?"
        sys.stderr.write("[update] ⚠️ 상류와 공통 조상이 없습니다 — 업스트림 이력 재작성(force-push)으로 보입니다.\n")
        sys.stderr.write("         유저 노드/데이터는 미추적이라 안전합니다.\n")
        if not a.resync:
            sys.stderr.write(
                "[update] 재동기화하려면: `./harness update --resync`\n"
                "         (현재 HEAD 를 'backup-before-resync' 브랜치로 백업한 뒤 `git reset --hard %s`).\n"
                "         로컬 플랫폼 커밋 %s개는 백업 브랜치에 보존됩니다. 커밋 안 된 변경은 먼저 커밋/스태시.\n"
                % (up, ahead))
            return 3
        if dirty:
            sys.stderr.write("[update] 커밋 안 된 변경이 있어 resync 불가 — 먼저 커밋/스태시.\n")
            return 1
        git("branch", "-f", "backup-before-resync", "HEAD")
        if git("reset", "--hard", up).returncode != 0:
            sys.stderr.write("[update] reset 실패.\n")
            return 1
        print("[update] '%s' 이력으로 재동기화 완료 (백업: backup-before-resync)." % up)
        _update_refresh()
        return 0

    # 1) Fast-forward if we haven't diverged — the common, clean case.
    if git("merge", "--ff-only", up).returncode == 0:
        print("[update] fast-forward 완료 (%s)." % up)
        _update_refresh()
        return 0

    # 2) Diverged. Refuse to merge over a dirty tree (would risk local work).
    dirty = git("status", "--porcelain", capture_output=True, text=True).stdout.strip()
    if dirty:
        sys.stderr.write("[update] 로컬에 커밋 안 된 변경이 있어 머지할 수 없습니다. 먼저 커밋/스태시:\n")
        sys.stderr.write(dirty + "\n")
        return 1

    # 3) Merge upstream (applies the patch); conflicting hunks get markers, not dropped.
    print("[update] fast-forward 불가(이력 분기) → 머지: %s" % up)
    git("merge", "--no-edit", up)
    conflicts = git("diff", "--name-only", "--diff-filter=U",
                    capture_output=True, text=True).stdout.split()
    if not conflicts:
        print("[update] 머지 완료(충돌 없음).")
        _update_refresh()
        return 0

    # 4) Conflicts remain — report precisely. The agent (AGENTS.md §5) resolves markers,
    #    validates, commits the merge, and tells the user what auto-resolved vs. needs review.
    sys.stderr.write("[update] ⚠️ 충돌 — 아래 파일에 충돌 마커가 있습니다(에이전트가 해결):\n")
    for f in conflicts:
        sys.stderr.write("   CONFLICT: %s\n" % f)
    sys.stderr.write(
        "[update] 해결: 각 파일의 <<<<<<< ======= >>>>>>> 정리 → `git -C %s add <file>` →\n"
        "         `git -C %s commit --no-edit` → `make ready`.  되돌리기: `git -C %s merge --abort`.\n"
        % (ROOT, ROOT, ROOT))
    return 3   # distinct code: conflicts to resolve


def cmd_mcp(a):
    import wire_mcp
    return wire_mcp.wire(a.harness, getattr(a, "node", None))


def cmd_tool(a):
    """Run a bundled toolkit tool: harness tool <name> -- <args>.
    Executes `python -m <entry.module>` from the tool node's repo/ using the platform venv."""
    import subprocess
    import yaml
    nd = os.path.join(ROOT, "toolkit", "%s-node" % a.name)
    man = os.path.join(nd, "manifest.yaml")
    if not os.path.exists(man):
        avail = []
        tdir = os.path.join(ROOT, "toolkit")
        if os.path.isdir(tdir):
            avail = [d[:-5] for d in sorted(os.listdir(tdir)) if d.endswith("-node")]
        sys.stderr.write("[tool] 없음: %s. 사용 가능: %s\n" % (a.name, ", ".join(avail) or "(없음)"))
        return 2
    spec = (yaml.safe_load(open(man, encoding="utf-8")) or {}).get("tool", {})
    entry = spec.get("entry", {}) or {}
    module = entry.get("module")
    if not module:
        sys.stderr.write("[tool] manifest 에 tool.entry.module 없음\n")
        return 2
    repo = os.path.join(nd, (spec.get("link", {}) or {}).get("path", "repo"))
    passthru = list(a.args or [])
    if passthru and passthru[0] == "--":
        passthru = passthru[1:]
    if not passthru:
        passthru = entry.get("watch_args", [])   # default args (e.g. --watch)
    py = os.path.join(ROOT, ".venv", "bin", "python")
    if not os.path.exists(py):
        py = sys.executable
    env = dict(os.environ, PYTHONPATH=repo + os.pathsep + os.environ.get("PYTHONPATH", ""))
    return subprocess.call([py, "-m", module] + passthru, cwd=repo, env=env)


def cmd_start(a):
    import session
    skip = True if a.skip_perms else (False if a.no_skip_perms else None)
    return session.start(session=a.session, harness=a.harness, skip_perms=skip,
                         cwd=a.cwd, use_tmux=not a.no_tmux, attach=not a.no_attach)


def cmd_standup(a):
    import standup
    nd = resolve_node(a.node)
    if a.list:
        print("\n".join(standup.list_days(nd)) or "(없음)")
        return 0
    did = False
    if a.add:
        print("[standup] + %s" % standup.add(nd, a.add, a.date)); did = True
    if a.today is not None or a.tomorrow is not None:
        print("[standup] 요약 %s" % standup.set_summary(nd, a.today, a.tomorrow, a.date)); did = True
    if a.show or not did:
        sys.stdout.write(standup.show(nd, a.date) or "(스탠드업 없음 — --add 로 시작)\n")
    return 0


def cmd_models(a):
    import llm
    return llm.audit()


def cmd_syncskills(a):
    import sync_skills
    return sync_skills.sync(getattr(a, "node", None), a.link)


def _write_enabled(names):
    """Rewrite only the top-level `enabled:` line in harnesses.yaml, preserving comments."""
    import registry
    lines = open(registry.PATH, encoding="utf-8").read().splitlines()
    rendered = "enabled: [%s]" % ", ".join('"%s"' % n for n in names)
    for i, ln in enumerate(lines):
        s = ln.lstrip()
        if s.startswith("enabled:") and not s.startswith("#"):
            lines[i] = rendered
            break
    else:
        lines.append(rendered)
    open(registry.PATH, "w", encoding="utf-8").write("\n".join(lines) + "\n")


def cmd_use(a):
    """Dynamically wire the platform to a harness: enable it in the registry, then
    (re)generate its entry-rule symlink and project skills/commands. Idempotent."""
    import registry, gen_agent_rules, sync_skills
    reg = registry.load()
    known = reg.get("harnesses") or {}
    if a.harness not in known:
        sys.stderr.write("[use] unknown harness '%s'. known: %s\n"
                         % (a.harness, ", ".join(sorted(known)) or "(none)"))
        return 2
    cur = list(reg.get("enabled") or [])
    if a.harness in cur:
        print("[use] '%s' already enabled" % a.harness)
    else:
        cur.append(a.harness)
        _write_enabled(cur)
        print("[use] enabled '%s' in platform/harnesses.yaml" % a.harness)
    gen_agent_rules.generate()
    sync_skills.sync()
    cfg = known[a.harness] or {}
    print("[use] '%s' wired — entry rules (%s) + skills projected."
          % (a.harness, cfg.get("rules_file", "?")))
    print("[use] MCP gateway (optional, harness-specific): copy adapters/mcp.example.json "
          "into this harness's MCP config and set NODE_DIR — see docs/USAGE.md.")
    return 0


def cmd_wikicompile(a):
    import wiki_compile
    res = wiki_compile.auto_merge(resolve_node(a.node))
    print("[wiki-compile] %s — %s" % (res.get("status"), res.get("msg") or res.get("entities")))
    return 0 if res.get("status") in ("merged", "empty", "no-llm") else 1


def cmd_wiki(a):
    import wiki
    node = resolve_node(a.node)
    if a.reindex:
        print("[wiki] INDEX 재생성: %s" % wiki.reindex(node))
    if a.embed:
        import router
        print("[wiki] 임베딩 청크: %d" % wiki.embed_all(node, router._load_embedder()))
    if a.links:
        rep = wiki.link_report(node)
        print("[wiki] dangling 링크: %s" % (rep["dangling"] or "없음"))
    if not (a.reindex or a.embed or a.links):
        pages = wiki.list_pages(node)
        for s in pages:
            print("  %-30s links=%s" % (s, wiki.read(node, s)["links"] or "-"))
        if not pages:
            print("  (엔티티 페이지 없음 — route=wiki 로 인제스트하거나 wiki_upsert)")
    return 0


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
    res = _server_for(a.node).search_all(a.query, a.k)
    for h in res.get("hits", []):
        print("[%-4s] %-24s dist=%.3f  %s"
              % (h.get("kind", "?"), h["doc_id"], h["distance"], h["text"][:70].replace("\n", " ").strip()))
    for m in res.get("sql_matches", []):
        print("[sql ] %s.%s (%s) — query 로 정확값 조회" % (m["db"], m["table"], ",".join(m["columns"])))
    if not res.get("hits") and not res.get("sql_matches"):
        print("(결과 없음)")
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
    sub = ap.add_subparsers(dest="cmd", required=False)

    p = sub.add_parser("init"); p.add_argument("name")
    p.add_argument("--link-type", default="path", choices=["path", "git-submodule", "git-clone", "symlink"])
    p.add_argument("--url"); p.add_argument("--ref"); p.add_argument("--force", action="store_true")
    p.add_argument("--target", help="link-type=symlink 의 대상 디렉토리(절대경로 권장)")
    p.add_argument("--private", action="store_true", help="기밀 노드: 데이터/산출물 미추적")
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("gen-rules"); p.add_argument("--node", default=None)
    p.set_defaults(fn=cmd_genrules)

    p = sub.add_parser("validate"); p.add_argument("node", nargs="?", default=None)
    p.add_argument("--strict", action="store_true", help="경고도 실패로 처리")
    p.set_defaults(fn=cmd_validate)

    p = sub.add_parser("install-hooks"); p.set_defaults(fn=cmd_installhooks)

    p = sub.add_parser("update", help="플랫폼 업데이트(ff/머지) + 의존성/훅/진입규칙 갱신")
    p.add_argument("--resync", action="store_true",
                   help="상류 이력 재작성 시 HEAD 백업 후 origin 으로 hard reset")
    p.set_defaults(fn=cmd_update)

    p = sub.add_parser("models"); p.set_defaults(fn=cmd_models)

    p = sub.add_parser("sync-skills"); p.add_argument("--node", default=None)
    p.add_argument("--link", action="store_true", help="복제 대신 심볼릭 링크(POSIX 전용)")
    p.set_defaults(fn=cmd_syncskills)

    p = sub.add_parser("use", help="하네스 동적 주입: enabled 추가 + 진입규칙/스킬 생성")
    p.add_argument("harness", help="claude-code | cursor | gemini | copilot")
    p.set_defaults(fn=cmd_use)

    p = sub.add_parser("mcp", help="MCP 와이어링: substrate(노드) + 외부 MCP(jira/figma 등)를 하네스 설정으로 병합")
    p.add_argument("harness", help="claude-code | cursor")
    p.add_argument("--node", default=None, help="이 노드의 substrate 서버도 포함(예: my_proj)")
    p.set_defaults(fn=cmd_mcp)

    p = sub.add_parser("tool", help="toolkit 번들 도구 실행: harness tool <name> -- <args>")
    p.add_argument("name", help="toolkit 노드 이름(예: ai-usage-monitor)")
    p.add_argument("args", nargs=argparse.REMAINDER, help="-- 뒤의 인자는 도구로 전달")
    p.set_defaults(fn=cmd_tool)

    p = sub.add_parser("start", help="작업 세션 시작: 하네스 선택/기본값 + tmux(좌 claude/우상 git watch/우하 usage)")
    p.add_argument("session", nargs="?", default="harness", help="tmux 세션 이름(예: els2.0)")
    p.add_argument("--harness", choices=["claude-code", "cursor"], default=None, help="기본값 무시하고 지정")
    p.add_argument("--skip-perms", action="store_true", help="claude --dangerously-skip-permissions 로 실행")
    p.add_argument("--no-skip-perms", action="store_true", help="claude 를 기본 권한으로 실행")
    p.add_argument("--cwd", default=None, help="claude 를 실행할 디렉토리(미지정 시 선택/기본값)")
    p.add_argument("--no-tmux", action="store_true", help="tmux 없이 claude 만 실행")
    p.add_argument("--no-attach", action="store_true", help="세션만 구성하고 attach 안 함(테스트/원격)")
    p.set_defaults(fn=cmd_start)

    p = sub.add_parser("standup", help="일 단위 스탠드업 로그(진행사항/요약): history/standup/<날짜>.md")
    p.add_argument("node")
    p.add_argument("--add", default=None, help="[진행사항] 에 항목 추가")
    p.add_argument("--today", default=None, help="[요약] 오늘 진행 중")
    p.add_argument("--tomorrow", default=None, help="[요약] 내일 예정")
    p.add_argument("--date", default=None, help="대상 날짜(기본 오늘)")
    p.add_argument("--show", action="store_true", help="해당 날짜 출력")
    p.add_argument("--list", action="store_true", help="기록된 날짜 목록")
    p.set_defaults(fn=cmd_standup)

    p = sub.add_parser("wiki"); p.add_argument("node")
    p.add_argument("--reindex", action="store_true"); p.add_argument("--embed", action="store_true")
    p.add_argument("--links", action="store_true", help="dangling [[link]] 리포트")
    p.set_defaults(fn=cmd_wiki)

    p = sub.add_parser("wiki-compile"); p.add_argument("node")  # 키 있을 때 LLM 자동 병합(없으면 no-op)
    p.set_defaults(fn=cmd_wikicompile)

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
    ap = build_parser()
    a = ap.parse_args()
    if not getattr(a, "fn", None):   # bare `harness` (no subcommand) → friendly help, not error
        ap.print_help()
        sys.exit(0)
    sys.exit(a.fn(a))


if __name__ == "__main__":
    main()
