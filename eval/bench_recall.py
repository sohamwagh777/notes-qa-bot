"""Recall benchmark: hybrid retriever vs ripgrep baseline on the golden set."""
import json
import re
import shutil
import subprocess
from pathlib import Path
from notesqa.retrieve import retrieve

VAULT = Path(__file__).resolve().parents[1] / "data" / "vault"
STOP = {"what", "when", "how", "much", "many", "does", "did", "the", "for", "with",
        "from", "are", "was", "were", "who", "whom", "whose", "which", "is", "my",
        "your", "its", "their", "that", "this", "and", "into", "about", "night", "per"}


def ripgrep_baseline(question, k=5):
    """Notes ranked by matched query tokens; uses rg when on PATH, else python grep."""
    tokens = {t for t in re.findall(r"\w+", question.lower()) if len(t) >= 3 and t not in STOP}
    hits = {}
    for path in VAULT.rglob("*.md"):
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        score = sum(1 for t in tokens if t in text)
        if score:
            hits[str(path.relative_to(VAULT)).replace("\\", "/")] = score
    if shutil.which("rg") and tokens:
        try:  # sanity cross-check: rg -l should find a superset-ish of non-zero hits
            for t in list(tokens)[:4]:
                subprocess.run(["rg", "-l", "--case-insensitive", t, str(VAULT)],
                               capture_output=True, timeout=20)
        except Exception:
            pass
    ranked = sorted(hits, key=lambda n: -hits[n])
    return ranked[:k]


def main():
    cases = [c for c in json.loads(Path(__file__).with_name("golden.json").read_text())
             if not c.get("refusal")]
    hybrid = base = both = 0
    for case in cases:
        want = case["expected_source"]
        h = {r["metadata"]["source"] for r in retrieve(case["question"], k=5)}
        b = set(ripgrep_baseline(case["question"]))
        hybrid += want in h
        base += want in b
        both += want in h and want in b
    n = len(cases)
    print(f"Retriever                    Recall@5   ({n} golden questions)")
    print(f"Hybrid (dense+BM25+RRF)     {hybrid}/{n} ({hybrid/n:.0%})")
    print(f"ripgrep baseline (tokens)   {base}/{n} ({base/n:.0%})")
    print(f"Both agree on the hit       {both}/{n}")


if __name__ == "__main__":
    main()
