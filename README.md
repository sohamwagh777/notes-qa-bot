# notes-qa-bot

**100% local RAG over your personal notes vault** (Obsidian-style markdown folder).
Ask questions in plain English, get grounded answers citing the exact note,
plus related notes surfaced from the `[[wikilink]]` graph. Your notes and
questions never leave your machine — Ollama only, zero cloud.

Part of the [Career-Builds](https://github.com/sohamwagh777) program: 20 RAG
projects, one repo each.

## Quickstart

Requirements: Python 3.12+, pinned deps, and a running
[Ollama](https://ollama.com) with `nomic-embed-text` + `bonsai-2:4b`.

```bash
python -m pip install -r requirements.txt
ollama pull nomic-embed-text && ollama pull bonsai-2:4b
PYTHONPATH=src python -m notesqa ingest --data data/vault
PYTHONPATH=src python -m notesqa ask "What is my bench press working weight?"
PYTHONPATH=src python -m notesqa list
PYTHONPATH=src python -m notesqa links gym-log
```

State lives in `~/.notesqa` (set `NOTESQA_HOME` to move it). Point `--data`
at your own vault — a sample one ships in `data/vault/`.

Streamlit UI (code-reviewed, not browser-tested): `streamlit run app.py`.

## Demo

Real terminal output from this build (RTX 3050 laptop, Ollama 0.40.14):

```text
$ PYTHONPATH=src python -m notesqa ingest --data data/vault
Indexed 10 notes: +10 new, ~0 changed, -0 pruned.
$ PYTHONPATH=src python -m notesqa ingest --data data/vault   # nothing changed
Indexed 10 notes: +0 new, ~0 changed, -0 pruned.
$ PYTHONPATH=src python -m notesqa ask "What is my bench press working weight?"
60kg [gym-log.md]
Citations: [gym-log.md]
Related: [home-gym.md], [meal-plan.md], [lisbon-trip.md], [books-to-read.md], [project-ideas.md]
$ PYTHONPATH=src python -m notesqa ask "When is the team demo and who presents it?"
The team demo is on Monday, and I am presenting it [meetings/standup-notes.md].
Citations: [meetings/standup-notes.md]
Related: [project-ideas.md]
$ PYTHONPATH=src python -m notesqa ask "What is my car insurance renewal date?"
NOT_IN_NOTES
$ PYTHONPATH=src python -m notesqa links gym-log
links -> home-gym, meal-plan, lisbon-trip
backlinks <- books-to-read.md, lisbon-trip.md, meal-plan.md, project-ideas.md
```

## How it works

- **Heading-aware chunking**: notes split only at `#/##/###` boundaries; every
  chunk carries its `H1 > H2 > H3` breadcrumb in the embedding text, so a
  passage can never be orphaned from its section context. Tiny siblings merge
  with their heading path preserved.
- **Hybrid retrieval**: dense top-12 (Chroma, cosine, `nomic-embed-text`) +
  BM25 top-12 fused with Reciprocal Rank Fusion (k=60). Exact terms like
  `18000` and paraphrases both land. Optional `--tag` filter on frontmatter tags.
- **Wikilink graph**: answers append `Related:` notes from `[[wikilinks]]`
  inside cited chunks plus incoming backlinks — vector search alone ignores
  the graph; this doesn't.
- **Incremental sync**: per-file sha256; unchanged notes are never re-embedded,
  changed ones replaced, deleted ones pruned (see the double-ingest demo above).

## Evaluation

12 hand-checked golden questions over the sample vault:

```text
Metric                  Score
Retrieval hit-rate      11/11 (100%)
Answer substring       11/11 (100%)
Refusal accuracy       1/1 (100%)
```

`PYTHONPATH=src python eval/run_eval.py` (needs Ollama + ingested vault).
Plus 12 pytest covering frontmatter, breadcrumbs, wikilinks/backlinks, RRF
math, tag filters, incremental behavior, and the refusal contract — all
network mocked.

## Limitations & upgrade path

Best-effort heading parsing inside code fences; backlinks are single-hop.
Logged upgrades: file-watcher daemon for live sync, Qdrant hybrid (BM25/
miniCOIL) payload filtering, bge-m3 embeddings, Ragas scoring, and a
ripgrep-recall benchmark harness.

## License

MIT. See [LICENSE](LICENSE).
