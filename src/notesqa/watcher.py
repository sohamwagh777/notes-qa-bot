"""Polling vault watcher: re-syncs the vault when note hashes change.

Stdlib-only daemon loop (no watchdog dependency). Extracted diff logic keeps
it testable without threads.
"""
import hashlib
import time
from pathlib import Path


def vault_hashes(dirpath):
    """Map relative note path -> content hash (or None if unreadable)."""
    out = {}
    for path in sorted(Path(dirpath).rglob("*.md")):
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            out[str(path.relative_to(dirpath)).replace("\\", "/")] = None
            continue
        out[str(path.relative_to(dirpath)).replace("\\", "/")] = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return out


def diff_vault(previous, current):
    """Return (added, changed, removed) relative-path tuples."""
    prev, cur = set(previous), set(current)
    added = tuple(sorted(cur - prev))
    removed = tuple(sorted(prev - cur))
    changed = tuple(sorted(k for k in prev & cur if previous[k] != current[k]))
    return added, changed, removed


def watch(dirpath, interval=5.0, on_change=None, max_ticks=None):
    """Poll `dirpath` every `interval`s; call on_change(stats) on any diff.

    max_ticks bounds the loop (tests / single passes); None runs forever.
    """
    last = vault_hashes(dirpath)
    ticks = 0
    while max_ticks is None or ticks < max_ticks:
        time.sleep(interval)
        ticks += 1
        now = vault_hashes(dirpath)
        added, changed, removed = diff_vault(last, now)
        if added or changed or removed:
            last = now
            stats = {"added": added, "changed": changed, "removed": removed}
            if on_change:
                on_change(stats)
        last = now
    return last
