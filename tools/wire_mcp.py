#!/usr/bin/env python3
"""wire_mcp — merge the substrate MCP server (per node) + enabled external MCP servers
(platform/mcp-servers.yaml) into a harness's MCP client config (.mcp.json / .cursor/mcp.json).

Secrets policy: external-server env values must reference env var NAMES via ${VAR};
secret values never live in the registry or this code. Generated configs are gitignored.
"""
from __future__ import annotations
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools", "lib"))
import registry  # platform/harnesses.yaml loader

MCP_REGISTRY = os.path.join(ROOT, "platform", "mcp-servers.yaml")
_PLAINTEXT_HINT = re.compile(r"(?i)(token|secret|key|password|passwd|pwd)")


def _load_external():
    """{name: cfg} for servers listed in `enabled` of mcp-servers.yaml."""
    if not os.path.exists(MCP_REGISTRY):
        return {}
    import yaml
    d = yaml.safe_load(open(MCP_REGISTRY, encoding="utf-8")) or {}
    servers = d.get("servers") or {}
    return {n: servers[n] for n in (d.get("enabled") or []) if n in servers}


def _check_secrets(servers):
    """Reject plaintext-looking secrets: a secret-ish env value must be a ${VAR} reference."""
    bad = []
    for name, cfg in servers.items():
        for k, v in (cfg.get("env") or {}).items():
            if _PLAINTEXT_HINT.search(k) and not (isinstance(v, str) and v.strip().startswith("${")):
                bad.append("%s.env.%s" % (name, k))
    return bad


def _wrap_external(cfg):
    """Run an external server through mcp_launch.py so it inherits credentials from .env.
    No env block is written to the config — secrets stay only in .env (gitignored)."""
    cmd = [cfg.get("command", "")] + [str(x) for x in (cfg.get("args") or [])]
    return {"command": ".venv/bin/python", "args": ["tools/mcp_launch.py", "--"] + cmd}


def _substrate_entry(node):
    return {
        "command": ".venv/bin/python",
        "args": ["mcp/server.py"],
        "env": {
            "NODE_DIR": "projects/%s-node" % node,
            "HARNESS_EMBED_BACKEND": "local",
            "HARNESS_EMBED_MODEL": "BAAI/bge-m3",
        },
    }


def wire(harness, node=None):
    hcfg = (registry.load().get("harnesses") or {}).get(harness)
    if hcfg is None:
        sys.stderr.write("[mcp] unknown harness '%s'\n" % harness)
        return 2
    cfgpath = hcfg.get("mcp_config")
    if not cfgpath:
        sys.stderr.write("[mcp] harness '%s' has no mcp_config in harnesses.yaml — "
                         "add one or wire manually.\n" % harness)
        return 2

    external = _load_external()
    bad = _check_secrets(external)
    if bad:
        sys.stderr.write("[mcp] plaintext secret suspected (use ${ENV_VAR}): %s\n" % ", ".join(bad))
        return 2

    servers = {}
    if node:
        servers["harness-%s" % node] = _substrate_entry(node)
    needed_env = []
    for n, cfg in external.items():
        servers[n] = _wrap_external(cfg)
        needed_env += list((cfg.get("env") or {}).keys())
    if not servers:
        sys.stderr.write("[mcp] nothing to wire — pass --node and/or enable servers in "
                         "platform/mcp-servers.yaml\n")
        return 1

    dst = os.path.join(ROOT, cfgpath)
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    existing = {}
    if os.path.exists(dst):
        try:
            existing = json.load(open(dst, encoding="utf-8"))
        except Exception:
            existing = {}
    existing.setdefault("mcpServers", {})
    existing["mcpServers"].update(servers)
    json.dump(existing, open(dst, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

    print("[mcp] wired %d server(s) → %s" % (len(servers), cfgpath))
    for n in servers:
        print("   - %s" % n)
    if needed_env:
        print("[mcp] 자격증명/설정은 .env (gitignored) 에 넣으세요 — 기동 시 자동 주입(export 불필요):")
        for k in dict.fromkeys(needed_env):
            print("        %s=..." % k)
    return 0


def main():
    import argparse
    ap = argparse.ArgumentParser(description="merge substrate + external MCP into a harness config")
    ap.add_argument("harness")
    ap.add_argument("--node", default=None)
    a = ap.parse_args()
    sys.exit(wire(a.harness, a.node))


if __name__ == "__main__":
    main()
