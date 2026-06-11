"""locks — 노드/티켓 단위 advisory 락 (state/lock.json). 동시 작업 충돌 방지.

원자적 생성(O_EXCL)으로 획득, stale(프로세스 사망 또는 TTL 초과) 자동 회수.
"""
from __future__ import annotations
import contextlib
import json
import os
import time

__tool_version__ = "0.1.0"


class LockError(Exception):
    pass


def _path(node_dir, name="lock"):
    return os.path.join(node_dir, "state", "%s.json" % name)


def _alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False
    except PermissionError:
        return True


def read(node_dir, name="lock"):
    p = _path(node_dir, name)
    if not os.path.exists(p):
        return None
    try:
        return json.load(open(p))
    except Exception:
        return None


def _stale(info, ttl):
    if not info:
        return True
    if info.get("pid") and not _alive(info["pid"]):
        return True
    return (time.time() - info.get("acquired_at", 0)) > ttl


def acquire(node_dir, owner, ticket=None, scope="node", ttl=3600, name="lock"):
    p = _path(node_dir, name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    info = {"owner": owner, "ticket": ticket, "scope": scope,
            "pid": os.getpid(), "acquired_at": time.time()}
    try:
        fd = os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        cur = read(node_dir, name)
        if _stale(cur, ttl):
            try:
                os.remove(p)
            except FileNotFoundError:
                pass
            return acquire(node_dir, owner, ticket, scope, ttl, name)
        raise LockError("이미 락 보유 중: owner=%s ticket=%s pid=%s" %
                        (cur.get("owner"), cur.get("ticket"), cur.get("pid")))
    with os.fdopen(fd, "w") as f:
        json.dump(info, f)
    return info


def release(node_dir, owner, name="lock"):
    cur = read(node_dir, name)
    if cur is None:
        return False
    if cur.get("owner") != owner:
        raise LockError("락 소유자 불일치: 보유=%s 시도=%s" % (cur.get("owner"), owner))
    os.remove(_path(node_dir, name))
    return True


@contextlib.contextmanager
def lock(node_dir, owner, ticket=None, scope="node", ttl=3600, name="lock"):
    acquire(node_dir, owner, ticket, scope, ttl, name)
    try:
        yield
    finally:
        try:
            release(node_dir, owner, name)
        except Exception:
            pass
