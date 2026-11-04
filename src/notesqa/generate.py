"""Grounded answers with [note.md] citations and related-note surfacing."""
import os, re, requests
from .links import wikilinks, backlinks

OLLAMA = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
MODEL = "bonsai-2:4b"
NOT_FOUND = "NOT_IN_NOTES"
EXTRACT_SYSTEM = ("One of the chunks below is topically related to the question, though it may use "
                  "different words. Reply with the exact sentence(s) from that chunk which answer it, "
                  "prefixed by its [filename] citation. No commentary, no preamble. "
                  "If truly nothing answers it, reply exactly NOT_IN_NOTES.")


def _meta_string(c):
    md = c["metadata"]
    return " ".join(str(md.get(k, "")) for k in ("source", "heading", "path", "title"))


def _chunk_score(question, c):
    """Weighted word-boundary match: 2 pts in heading/path/title, 1 pt in text."""
    score = 0
    for t in re.findall(r"\b\w{4,}\b", question.lower()):
        if re.search(rf"\b{re.escape(t)}\b", c["text"].lower()):
            score += 1
        if re.search(rf"\b{re.escape(t)}\b", _meta_string(c).lower()):
            score += 2
    return score


def _rare_overlap_tokens(question, chunks, max_df=3):
    """Query tokens (len>=4) that occur in 1..max_df chunks — specific enough to justify a retry."""
    qtoks = {t for t in re.findall(r"\b\w{4,}\b", question.lower())}
    if not qtoks or not chunks:
        return set()

    def present(c, t):
        return bool(re.search(rf"\b{re.escape(t)}\b", c["text"].lower())
                    or re.search(rf"\b{re.escape(t)}\b", _meta_string(c).lower()))
    return {t for t in qtoks if 1 <= sum(1 for c in chunks if present(c, t)) <= max_df}


def _prime(chunks, question):
    """Order chunks by weighted query-token match (heading/path first, then text),
    preserving RRF order on ties (stable sort)."""
    return sorted(chunks, key=lambda c: -_chunk_score(question, c))


def _extract_fallback(question, chunks):
    """Second, targeted call — only after a refusal, only when a chunk shares rare query tokens.
    Returns the extracted answer or None (keep the refusal)."""
    scored = [(len(_rare_overlap_tokens(question, [c])), i, c) for i, c in enumerate(chunks)]
    best_count, _, best = max(scored, key=lambda x: (x[0], -x[1]))
    if best_count < 1:
        return None  # nothing shares specific vocabulary: the refusal is probably correct
    payload = {"model": MODEL, "stream": False, "think": False,
               "options": {"temperature": 0.0, "num_predict": 200},
               "messages": [{"role": "system", "content": EXTRACT_SYSTEM},
                            {"role": "user", "content": f"Question: {question}\n\nChunk:\n"
                             f"[{best['metadata']['source']}]\n{best['text']}"}]}
    response = requests.post(f"{OLLAMA}/api/chat", json=payload, timeout=180)
    response.raise_for_status()
    value = response.json()["message"]["content"].strip()
    if NOT_FOUND in value or not value:
        return None
    if not re.search(r"\[[^\]\s]+\.md\]", value):  # force a real citation on the fallback path
        value += f" [{best['metadata']['source']}]"
    return value
SYSTEM = ("Answer ONLY using the supplied note chunks. Give a concise answer and cite every factual "
          "claim inline using the real note filename shown before each chunk, like [gym-log.md]. "
          "Never invent filenames. If the chunks do not contain the answer, reply exactly "
          "NOT_IN_NOTES. Do not use outside knowledge.")


def answer(question, chunks, notes=None):
    if not chunks:
        return {"answer": NOT_FOUND, "citations": [], "related": []}
    chunks = _prime(chunks, question)
    context = "\n\n".join(f"[{c['metadata']['source']}]\n{c['text']}" for c in chunks)
    response = requests.post(f"{OLLAMA}/api/chat", json={
        "model": MODEL, "stream": False, "think": False,
        "options": {"temperature": 0.0, "num_predict": 300},
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": f"Question: {question}\n\nChunks:\n{context}"}]}, timeout=180)
    response.raise_for_status()
    value = response.json()["message"]["content"].strip()
    if NOT_FOUND in value:
        extracted = _extract_fallback(question, chunks)
        if extracted:
            value = extracted
        else:
            return {"answer": NOT_FOUND, "citations": [], "related": []}
    citations = list(dict.fromkeys(
        c for c in re.findall(r"\[([^\]\s]+\.md)\]", value)))
    related = []
    seen_stems = set()

    def _push(cand):
        stem = cand.rsplit("/", 1)[-1].rsplit(".", 1)[0].lower()
        if stem not in seen_stems:
            seen_stems.add(stem)
            related.append(cand)

    if notes:
        for cite in citations:
            stem = cite.rsplit("/", 1)[-1].rsplit(".", 1)[0].lower()
            for src in {c["metadata"]["source"].rsplit("/", 1)[-1].rsplit(".", 1)[0].lower() for c in chunks}:
                if src == stem:
                    body = "\n".join(c["text"] for c in chunks
                                     if c["metadata"]["source"].rsplit("/", 1)[-1].rsplit(".", 1)[0].lower() == stem)
                    for link in wikilinks(body):
                        cand = link if link.endswith(".md") else link + ".md"
                        if cand.rsplit("/", 1)[-1].rsplit(".", 1)[0].lower() != stem:
                            _push(cand)
            for nb in backlinks(cite, notes):
                _push(nb)
    return {"answer": value, "citations": citations, "related": related[:5]}
