"""Command-line interface."""
import argparse
import os
from pathlib import Path
from .store import sync_notes, list_documents, get_collection
from .retrieve import retrieve
from .generate import answer


def _all_note_texts():
    col = get_collection()
    data = col.get(include=["documents", "metadatas"])
    notes = {}
    for t, m in zip(data["documents"], data["metadatas"]):
        notes.setdefault(m["source"], []).append(t)
    return {k: "\n".join(v) for k, v in notes.items()}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="notesqa", description="Local RAG Q&A over a markdown notes vault")
    sub = parser.add_subparsers(dest="command", required=True)
    ing = sub.add_parser("ingest"); ing.add_argument("--data", default="data/vault")
    ask = sub.add_parser("ask"); ask.add_argument("question"); ask.add_argument("--tag"); ask.add_argument("--k", type=int, default=5)
    sub.add_parser("list")
    ln = sub.add_parser("links"); ln.add_argument("note")
    wa = sub.add_parser("watch"); wa.add_argument("--data", default="data/vault"); wa.add_argument("--interval", type=float, default=5.0)
    args = parser.parse_args(argv)
    if args.command == "ingest":
        stats = sync_notes(Path(args.data))
        print(f"Indexed {stats['files']} notes: +{stats['added']} new, ~{stats['changed']} changed, -{stats['pruned']} pruned.")
    elif args.command == "list":
        docs = list_documents()
        if not docs:
            print("No notes indexed.")
        for name, item in sorted(docs.items()):
            print(f"{name} tags=[{item['tags']}] chunks={item['chunks']}")
    elif args.command == "links":
        from .links import wikilinks
        notes = _all_note_texts()
        target = args.note if args.note.endswith(".md") else args.note + ".md"
        matches = [n for n in notes if n.lower() == target.lower()]
        if not matches:
            print(f"Note not indexed: {target}")
            return
        name = matches[0]
        out = ", ".join(wikilinks(notes[name])) or "(none)"
        print(f"links -> {out}")
        from .links import backlinks
        back = ", ".join(backlinks(name, notes)) or "(none)"
        print(f"backlinks <- {back}")
    elif args.command == "watch":
        import subprocess
        import sys
        from .watcher import watch
        data = Path(args.data)
        print(f"Watching {data} every {args.interval}s (ctrl-c to stop)…")

        def on_change(stats):
            print(f"vault changed: +{len(stats['added'])} ~{len(stats['changed'])} "
                  f"-{len(stats['removed'])} — re-syncing")
            # fresh subprocess: Chroma's PersistentClient is not multi-process safe,
            # so the long-lived watcher loop must not hold a client itself.
            subprocess.run([sys.executable, "-m", "notesqa", "ingest", "--data", str(data)],
                           env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src")},
                           check=False)
        try:
            watch(data, interval=args.interval, on_change=on_change)
        except KeyboardInterrupt:
            print("stopped")
    else:
        chunks = retrieve(args.question, k=args.k, tag=args.tag)
        result = answer(args.question, chunks, notes=_all_note_texts())
        print(result["answer"])
        if result["citations"]:
            print("Citations: " + ", ".join(f"[{c}]" for c in result["citations"]))
        if result["related"]:
            print("Related: " + ", ".join(f"[{r}]" for r in result["related"]))


if __name__ == "__main__":
    main()
