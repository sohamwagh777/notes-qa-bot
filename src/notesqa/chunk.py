"""Heading-aware chunking: never orphan a passage from its heading breadcrumb."""
from .fm import parse_frontmatter

MIN_WORDS, MAX_WORDS = 150, 700

def _words(t): return len(t.split())

def chunk_note(name, text):
    """Split at heading boundaries; carry H1>H2>H3 breadcrumb per chunk."""
    meta, body = parse_frontmatter(text)
    chunks, stack, buf, buf_heading = [], {}, [], ""
    path = []

    def flush():
        nonlocal buf
        if not buf:
            return
        content = "\n".join(buf).strip()
        if content:
            chunks.append({"content": content, "heading": buf_heading or (path[-1] if path else name),
                           "path": " > ".join(path)})
        buf = []

    for line in body.splitlines():
        m = None if line.startswith("```") else __import__("re").match(r"^(#{1,3})\s+(.*)", line)
        if m:
            flush()
            level, title = len(m.group(1)), m.group(2).strip()
            path = path[: level - 1] + [title]
            stack[level] = title
            buf_heading = " > ".join(path)
        elif line.strip() and _words("\n".join(buf)) >= MAX_WORDS and not line.startswith(("- ", "|", "```")):
            flush()
            buf_heading = " > ".join(path) if path else name
        else:
            buf.append(line)
    flush()
    # merge tiny chunks into previous sibling
    merged = []
    for c in chunks:
        if merged and _words(c["content"]) < MIN_WORDS and _words(merged[-1]["content"]) < MAX_WORDS:
            merged[-1]["content"] += "\n\n" + c["content"]
            if c["heading"] not in merged[-1]["heading"]:
                merged[-1]["heading"] += " | " + c["heading"]
            merged[-1]["path"] += " | " + c["path"]
        else:
            merged.append(c)
    tags = meta.get("tags", [])
    if isinstance(tags, str):
        tags = [tags]
    return [{"text": c["content"],
             "embedding_text": f"Document: {name}\nTags: {', '.join(tags)}\nPath: {c['path']}\n\n{c['content']}",
             "metadata": {"source": name, "tags": ",".join(tags), "heading": c["heading"],
                          "path": c["path"], "title": meta.get("title", name)}}
            for c in merged]
