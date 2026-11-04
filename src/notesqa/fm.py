"""Minimal YAML-ish frontmatter parsing with stdlib only."""
import re

def parse_frontmatter(text):
    """Return (meta, body). Supports `key: value` and tags as [a, b] or - bullets."""
    meta = {}
    if not text.startswith("---"):
        return meta, text
    end = text.find("\n---", 3)
    if end == -1:
        return meta, text
    block = text[3:end].strip()
    body = text[end + 4:].lstrip("\n")
    key = None
    for line in block.splitlines():
        if re.match(r"^\s*-\s+", line) and key:
            meta.setdefault(key, [])
            if isinstance(meta[key], list):
                meta[key].append(line.split("-", 1)[1].strip())
            continue
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        key = k.strip()
        v = v.strip()
        if v.startswith("[") and v.endswith("]"):
            meta[key] = [t.strip() for t in v[1:-1].split(",") if t.strip()]
        elif v == "":
            meta[key] = []
        else:
            meta[key] = v
    return meta, body
