"""Chroma persistence, Ollama embeddings, content-hash incremental sync."""
import hashlib
import os
from pathlib import Path
import requests
import chromadb

OLLAMA = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
EMBED_MODEL = os.getenv("NOTESQA_EMBED_MODEL", "nomic-embed-text")
COLLECTION = f"notes-{EMBED_MODEL.split(':')[0]}"


def state_dir():
    return Path(os.getenv("NOTESQA_HOME", str(Path.home() / ".notesqa")))


def embed(texts):
    response = requests.post(f"{OLLAMA}/api/embed", json={"model": EMBED_MODEL, "input": texts}, timeout=120)
    response.raise_for_status()
    return response.json()["embeddings"]


def get_collection():
    client = chromadb.PersistentClient(path=str(state_dir()))
    return client.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})


def sync_notes(dirpath):
    """Incremental sync: embed only changed/new files; prune deleted ones."""
    col = get_collection()
    dirpath = Path(dirpath)
    files = sorted(p for p in dirpath.rglob("*.md"))
    from .chunk import chunk_note
    from .fm import parse_frontmatter
    indexed = {}
    for md in col.get(include=["metadatas"])["metadatas"]:
        indexed.setdefault(md["source"], set()).add(md.get("hash", ""))
    added = changed = pruned = 0
    current = set()
    for path in files:
        name = str(path.relative_to(dirpath)).replace("\\", "/")
        current.add(name)
        raw = path.read_text(encoding="utf-8", errors="replace")
        digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
        if digest in indexed.get(name, set()):
            continue
        old = col.get(where={"source": name})
        if old["ids"]:
            col.delete(ids=old["ids"])
            changed += 1 if name in indexed else 0
            added += 0 if name in indexed else 1
        else:
            added += 1
        _, body = parse_frontmatter(raw)
        chunks = chunk_note(name, raw)
        if not chunks:
            continue
        for start in range(0, len(chunks), 64):
            batch = chunks[start:start + 64]
            vectors = embed([c["embedding_text"] for c in batch])
            col.add(ids=[f"{name}::{digest}::{i+start}" for i in range(len(batch))],
                    documents=[c["text"] for c in batch],
                    embeddings=vectors,
                    metadatas=[{**c["metadata"], "hash": digest} for c in batch])
        _ = body
    for name in set(indexed) - current:
        old = col.get(where={"source": name})
        if old["ids"]:
            col.delete(ids=old["ids"])
        pruned += 1
    return {"added": added, "changed": changed, "pruned": pruned, "files": len(files)}


def list_documents():
    col = get_collection()
    data = col.get(include=["metadatas"])
    docs = {}
    for md in data["metadatas"]:
        item = docs.setdefault(md["source"], {"tags": md.get("tags", ""), "chunks": 0})
        item["chunks"] += 1
    return docs
