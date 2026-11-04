"""Hybrid retrieval: dense Chroma + BM25 + reciprocal rank fusion."""
import re
from rank_bm25 import BM25Okapi
from .store import embed, get_collection


def where_for(tag=None):
    # NOTE: chroma $contains on a comma-string is unreliable across versions —
    # tag filtering is done python-side in retrieve() against metadata["tags"].
    return None


def _tag_match(row, tag):
    if not tag:
        return True
    return tag.lower() in [t.strip().lower() for t in row["metadata"].get("tags", "").split(",")]


def rrf(rankings, k=60):
    scores = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, 1):
            key = item["id"] if isinstance(item, dict) else item
            scores[key] = scores.get(key, 0) + 1 / (k + rank)
    return sorted(scores, key=lambda x: scores[x], reverse=True)


def tokenize(text):
    return re.findall(r"\w+", text.lower())


def retrieve(query, k=5, tag=None, dense_n=12, bm25_n=12):
    col = get_collection()
    count = col.count()
    if not count:
        return []
    qvec = embed([query])[0]
    dense = col.query(query_embeddings=[qvec], n_results=min(dense_n * (2 if tag else 1), count))
    ids = dense["ids"][0]
    rows = {i: {"id": i, "text": t, "metadata": m}
            for i, t, m in zip(ids, dense["documents"][0], dense["metadatas"][0])}
    allrows = col.get(include=["documents", "metadatas"])
    corpus = [tokenize(x) for x in allrows["documents"]]
    bm_ids = []
    if corpus:
        bm = BM25Okapi(corpus)
        scores = bm.get_scores(tokenize(query))
        bm_ids = [allrows["ids"][i] for i in sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:bm25_n * (2 if tag else 1)] if scores[i] > 0]
        for i in bm_ids:
            pos = allrows["ids"].index(i)
            rows.setdefault(i, {"id": i, "text": allrows["documents"][pos], "metadata": allrows["metadatas"][pos]})
    ordered = rrf([ids, bm_ids])
    hits = [rows[i] for i in ordered if i in rows and _tag_match(rows[i], tag)]
    return hits[:k]
