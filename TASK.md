# TASK.md — notes-qa-bot (Career-Builds project #3)

Build a CLI-first, fully-local RAG Q&A tool over a personal notes vault
(Obsidian-style markdown folder). 100% local story: Ollama only, nothing
leaves the machine. House style: lean stack, pinned deps, pytest + golden
eval, Streamlit UI, Dockerfile, MIT.

## Corpus
`data/vault/` contains ~9 realistic notes with YAML frontmatter (tags, date),
`#`/`##`/`###` headings, `[[wikilinks]]` between notes, and factual content
(see golden set). Do NOT change corpus files — they are the test fixtures.

## Package layout (mirror syllabus-qa-bot conventions)
```
src/notesqa/
  __init__.py __main__.py
  fm.py        # YAML frontmatter parse with stdlib only (no pyyaml): key: value, tags lists inline [a, b] or - bullets
  chunk.py     # heading-aware chunking: each chunk carries breadcrumb "H1 > H2 > H3" prefix in embedding_text
  links.py     # extract [[wikilinks]] from a note; find backlinks (notes whose links point at a note)
  store.py     # chromadb PersistentClient at NOTESQA_HOME env (default ~/.notesqa); embed via Ollama nomic-embed-text at OLLAMA_HOST (default http://127.0.0.1:11434); content-hash based incremental sync
  retrieve.py  # dense chroma query + BM25Okapi over filtered corpus + reciprocal rank fusion (k=60); optional --tag filter on metadata
  generate.py  # Ollama chat, model bonsai-2:4b, temperature 0, think False, num_predict 256; answer ONLY from chunks; cite every claim with [note.md]; if chunks empty or insufficient reply exactly NOT_IN_NOTES
  cli.py       # subcommands: ingest [--data DIR], ask QUESTION [--tag T] [--k N], list, links NOTE
```

## Hard requirements
1. **Heading-aware chunks**: split at heading boundaries; keep heading breadcrumb in `embedding_text` as `Document: <name>\nTags: <tags>\nPath: <H2 > H3>\n\n<text>`; chunks carry metadata {source, tags, heading, path, hash}. Never orphan context from its heading. Chunk target 150–700 words, merge tiny siblings.
2. **Incremental sync**: per-file sha256; unchanged files skipped, changed files replaced, deleted files pruned. `list` prints per-note tag + chunk counts. Prove with a test that re-ingest of unchanged vault does not re-embed (count embed calls with a mock).
3. **Wikilinks/backlinks**: `notesqa links gym-log` prints outgoing `[[links]]` and incoming backlinks. `ask` appends a "Related: [note.md]" line for notes linked from cited chunks.
4. **Citations**: only real note filenames like `[gym-log.md]` — never placeholder words. Refusal path returns exactly NOT_IN_NOTES with no citations.
5. **Tests** ≥10 pytest in tests/ (mock all network via patch on requests.post): frontmatter parsing (inline + bullet tags), breadcrumb chunking, wikilink extraction, backlinks, incremental sync skip + prune, RRF math, citation formatting, empty-retrieval refusal without LLM call, NOT_IN_NOTES passthrough, tag filter builder.
6. **Golden eval** eval/golden.json + eval/run_eval.py: ≥10 cases with {question, expected_source, expected_substring} and ≥1 refusal case (e.g. "what is my car's insurance renewal date?" -> NOT_IN_NOTES). Print retrieval hit-rate, answer-substring, refusal accuracy like syllabus-qa-bot.
7. **README.md**: what/why/how, quickstart, demo block PLACEHOLDER `<!--DEMO-->` (controller captures real output later), how-it-works, eval section with `<!--EVAL-->` placeholder, limitations + upgrade paths (Qdrant hybrid, bge-m3, Ragas, file-watcher daemon), MIT.
8. **Dockerfile** python:3.12-slim, COPY src + data/vault, ENV PYTHONPATH=/app/src, ENTRYPOINT python -m notesqa. **app.py** Streamlit UI: question box, tag select from corpus tags, answers + citations + related notes.
9. `requirements.txt` EXACTLY: chromadb==1.5.9, rank_bm25==0.2.2, pytest==9.1.1, requests==2.34.2, streamlit==1.66.1 — stdlib for everything else (no pyyaml, no LlamaIndex).

## Style
Compact readable code, module docstrings, no dead code, no TODOs. Do not
commit or push anything. Do not touch files outside this repo.
