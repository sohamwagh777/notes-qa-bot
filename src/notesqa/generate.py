"""Grounded answers with [note.md] citations and related-note surfacing."""
import os, re, requests
from .links import wikilinks, backlinks

OLLAMA = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
MODEL = "bonsai-2:4b"
NOT_FOUND = "NOT_IN_NOTES"
SYSTEM = ("Answer ONLY using the supplied note chunks. Give a concise answer and cite every factual "
          "claim inline using the real note filename shown before each chunk, like [gym-log.md]. "
          "Never invent filenames. If the chunks do not contain the answer, reply exactly "
          "NOT_IN_NOTES. Do not use outside knowledge.")


def answer(question, chunks, notes=None):
    if not chunks:
        return {"answer": NOT_FOUND, "citations": [], "related": []}
    context = "\n\n".join(f"[{c['metadata']['source']}]\n{c['text']}" for c in chunks)
    response = requests.post(f"{OLLAMA}/api/chat", json={
        "model": MODEL, "stream": False, "think": False,
        "options": {"temperature": 0.0, "num_predict": 300},
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": f"Question: {question}\n\nChunks:\n{context}"}]}, timeout=180)
    response.raise_for_status()
    value = response.json()["message"]["content"].strip()
    if NOT_FOUND in value:
        return {"answer": NOT_FOUND, "citations": [], "related": []}
    citations = list(dict.fromkeys(
        c for c in re.findall(r"\[([^\]\s]+\.md)\]", value)))
    related = []
    if notes:
        for cite in citations:
            stem = cite.rsplit(".", 1)[0].lower()
            for src in {c["metadata"]["source"].rsplit(".", 1)[0].lower() for c in chunks}:
                if src == stem:
                    body = "\n".join(c["text"] for c in chunks if c["metadata"]["source"].rsplit(".", 1)[0].lower() == stem)
                    for link in wikilinks(body):
                        cand = link if link.endswith(".md") else link + ".md"
                        if cand.lower() != cite.lower() and cand not in related:
                            related.append(cand)
            if notes:  # incoming backlinks
                for nb in backlinks(cite, notes):
                    if nb not in related:
                        related.append(nb)
    return {"answer": value, "citations": citations, "related": related[:5]}
