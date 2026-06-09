"""registry — 하네스 어댑터 레지스트리 로더 (platform/harnesses.yaml).

핵심 플랫폼을 하네스 중립으로 유지하기 위한 단일 옵트인 지점. gen_agent_rules / sync_skills 가
이 레지스트리의 `enabled` 만 보고 로컬 산출물을 만든다(미추적).
"""
from __future__ import annotations
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # tools/lib/ → 루트
PATH = os.path.join(ROOT, "platform", "harnesses.yaml")


def load() -> dict:
    if not os.path.exists(PATH):
        return {"harnesses": {}, "enabled": []}
    import yaml
    return yaml.safe_load(open(PATH, encoding="utf-8")) or {"harnesses": {}, "enabled": []}


def enabled() -> list:
    """[(name, cfg), ...] — enabled 에 있고 harnesses 에 정의된 것만."""
    d = load()
    reg = d.get("harnesses", {}) or {}
    out = []
    for name in (d.get("enabled") or []):
        if name in reg:
            out.append((name, reg[name] or {}))
    return out
