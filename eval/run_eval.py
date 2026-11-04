"""Run retrieval and answer checks against the hand-checked golden set."""
import json
from pathlib import Path
from notesqa.retrieve import retrieve
from notesqa.generate import answer, NOT_FOUND


def main():
    cases = json.loads(Path(__file__).with_name("golden.json").read_text())
    hit = contains = refusal = 0
    verbose = "--verbose" in __import__("sys").argv
    for case in cases:
        rows = retrieve(case["question"], k=5, tag=case.get("tag"))
        if case.get("refusal"):
            ok = answer(case["question"], rows)["answer"] == NOT_FOUND
            refusal += ok
        else:
            got_src = any(r["metadata"]["source"] == case["expected_source"] for r in rows)
            hit += got_src
            got_ans = case["expected_substring"].lower() in answer(case["question"], rows)["answer"].lower()
            contains += got_ans
            ok = got_src and got_ans
        if verbose:
            print(("PASS" if ok else "FAIL"), "|", case["question"][:58])
    total = len(cases)
    answer_total = sum(1 for c in cases if not c.get("refusal"))
    refusal_total = total - answer_total
    print("Metric                  Score")
    print(f"Retrieval hit-rate      {hit}/{answer_total} ({hit/answer_total:.0%})")
    print(f"Answer substring       {contains}/{answer_total} ({contains/answer_total:.0%})")
    print(f"Refusal accuracy       {refusal}/{refusal_total} ({refusal/refusal_total:.0%})")
    if verbose:
        print(f"Cases                  {sum(1 for c in cases)}/{total}")


if __name__ == "__main__":
    main()
