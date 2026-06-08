"""provenance — info/index.yaml 출처 기록 유틸 (stdlib only)."""
from __future__ import annotations
import hashlib, json, os, datetime, pathlib

__tool_version__ = "0.1.0"

def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()

def _index_path(node_dir: str) -> str:
    return os.path.join(node_dir, "info", "index.yaml")

def load_index(node_dir: str) -> dict:
    # 의존성 회피를 위해 YAML 대신 JSON으로 안전 파싱 시도; 없으면 새로 생성.
    p = _index_path(node_dir)
    if os.path.exists(p):
        try:
            import yaml  # optional
            return yaml.safe_load(open(p)) or {"schema_version": 1, "entries": []}
        except Exception:
            return {"schema_version": 1, "entries": []}
    return {"schema_version": 1, "entries": []}

def record(node_dir: str, *, entry_id: str, store: str, location: str,
           source: str, tool: str, supersedes=None, dry_run=False) -> dict:
    """info/index.yaml 에 한 entry 추가(멱등: 동일 source+sha면 skip)."""
    sha = sha256_of(source)
    entry = {
        "id": entry_id, "store": store, "location": location,
        "source": os.path.relpath(source, node_dir), "sha256": sha,
        "ingested_at": datetime.datetime.utcnow().isoformat() + "Z",
        "tool": tool, "supersedes": supersedes or [],
    }
    idx = load_index(node_dir)
    if any(e.get("sha256") == sha and e.get("source") == entry["source"] for e in idx["entries"]):
        return {"status": "skip-duplicate", "entry": entry}
    if dry_run:
        return {"status": "dry-run", "entry": entry}
    idx["entries"].append(entry)
    p = _index_path(node_dir)
    pathlib.Path(os.path.dirname(p)).mkdir(parents=True, exist_ok=True)
    try:
        import yaml
        yaml.safe_dump(idx, open(p, "w"), allow_unicode=True, sort_keys=False)
    except Exception:
        json.dump(idx, open(p, "w"), ensure_ascii=False, indent=2)
    return {"status": "recorded", "entry": entry}
