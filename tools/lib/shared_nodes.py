"""shared_nodes — resolve a node's opt-in shared-knowledge nodes (manifest `node.shares`).

Cross-project common data (conventions, reference docs, shared wiki/RAG/SQL) lives in a
dedicated shared node (e.g. `projects/_shared-node`) and is ingested ONCE there. A project
opts in by declaring `node.shares: [_shared]` in its manifest; search/read then federate
over the node's own `info/` + each shared node's `info/` (the shared node is read-only from
the project's perspective). No duplication, single update point.
"""
from __future__ import annotations
import os


def _projects_dir(node_dir):
    return os.path.dirname(os.path.abspath(node_dir))


def declared(node_dir):
    """Names listed in manifest `node.shares` (empty list if none/unreadable)."""
    man = os.path.join(node_dir, "manifest.yaml")
    if not os.path.exists(man):
        return []
    try:
        import yaml
        m = yaml.safe_load(open(man, encoding="utf-8")) or {}
    except Exception:
        return []
    sh = (m.get("node") or {}).get("shares") or []
    return [str(s) for s in sh] if isinstance(sh, list) else []


def resolve(node_dir):
    """Resolve declared shares to existing sibling node dirs (absolute paths), excluding self.

    A bare name `foo` resolves to `<projects>/foo-node`; `foo-node` is taken as-is; an
    absolute path is used verbatim. Missing targets are silently dropped (validate warns)."""
    pdir = _projects_dir(node_dir)
    self_abs = os.path.abspath(node_dir)
    out = []
    for name in declared(node_dir):
        if os.path.isabs(name):
            cand = name
        else:
            base = name if name.endswith("-node") else "%s-node" % name
            cand = os.path.join(pdir, base)
        cand = os.path.abspath(cand)
        if cand == self_abs or cand in out:
            continue
        if os.path.isdir(cand):
            out.append(cand)
    return out
