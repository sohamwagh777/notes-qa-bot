from unittest.mock import patch
from notesqa.fm import parse_frontmatter
from notesqa.chunk import chunk_note
from notesqa.links import wikilinks, backlinks
from notesqa.retrieve import rrf, where_for
from notesqa.generate import answer, NOT_FOUND


def test_frontmatter_inline_tags():
    meta, body = parse_frontmatter("---\ntitle: X\ntags: [a, b]\n---\n# H\nbody")
    assert meta["tags"] == ["a", "b"] and meta["title"] == "X" and body.startswith("# H")


def test_frontmatter_bullet_tags():
    meta, _ = parse_frontmatter("---\ntags:\n- gym\n- log\n---\ntext")
    assert meta["tags"] == ["gym", "log"]


def test_frontmatter_absent():
    meta, body = parse_frontmatter("# plain\nno fm")
    assert meta == {} and body.startswith("# plain")


def test_breadcrumb_in_embedding_text():
    c = chunk_note("n.md", "# T\n## S\n\n" + "word " * 200)[0]
    assert "Path: T > S" in c["embedding_text"] and "Document: n.md" in c["embedding_text"]
    assert c["metadata"]["heading"] == "T > S"


def test_heading_not_orphaned():
    text = "# A\n## B\n\nfact one here\n\n## C\n\nfact two here"
    chunks = chunk_note("a.md", text)
    assert any("fact one" in c["text"] and "B" in c["metadata"]["path"] for c in chunks)
    assert any("fact two" in c["text"] and "C" in c["metadata"]["path"] for c in chunks)


def test_wikilinks_dedup_order():
    assert wikilinks("[[a]] and [[b]] and [[a|alias]]") == ["a", "b"]


def test_backlinks():
    notes = {"x.md": "see [[y]]", "y.md": "plain", "z.md": "see [[x.md]]"}
    assert backlinks("y.md", notes) == ["x.md"]
    assert backlinks("x.md", notes) == ["z.md"]


def test_rrf_math():
    assert rrf([["a", "b"], ["a", "c"]], k=60) == ["a", "b", "c"]


def test_tag_filter_match():
    from notesqa.retrieve import _tag_match
    row = {"metadata": {"tags": "fitness,cooking"}}
    assert _tag_match(row, "cooking") and _tag_match(row, "fitness")
    assert not _tag_match(row, "travel") and _tag_match(row, None)


def test_empty_retrieval_refuses_without_llm():
    with patch("notesqa.generate.requests.post") as post:
        assert answer("anything", [])["answer"] == NOT_FOUND
        post.assert_not_called()


def test_not_in_notes_passthrough():
    chunks = [{"text": "x", "metadata": {"source": "a.md"}}]
    with patch("notesqa.generate.requests.post") as post:
        post.return_value.raise_for_status.return_value = None
        post.return_value.json.return_value = {"message": {"content": NOT_FOUND}}
        assert answer("q", chunks)["answer"] == NOT_FOUND


def test_citation_extraction_real_filenames():
    chunks = [{"text": "bench 60kg", "metadata": {"source": "gym-log.md"}}]
    with patch("notesqa.generate.requests.post") as post:
        post.return_value.raise_for_status.return_value = None
        post.return_value.json.return_value = {"message": {"content": "Bench is 60kg [gym-log.md]."}}
        r = answer("bench?", chunks)
        assert r["citations"] == ["gym-log.md"] and "[filename" not in r["answer"]


def test_related_dedupes_subfolder_stems():
    chunks = [{"text": "rent 18000, plan see [[budget-2026]]", "metadata": {"source": "finance/budget-2026.md"}}]
    notes = {"finance/budget-2026.md": "rent 18000 [[budget-2026]]", "gym-log.md": "cites [[finance/budget-2026]]"}
    with patch("notesqa.generate.requests.post") as post:
        post.return_value.raise_for_status.return_value = None
        post.return_value.json.return_value = {"message": {"content": "Rent is 18000 [finance/budget-2026.md]."}}
        r = answer("rent?", chunks, notes=notes)
        stems = [x.rsplit("/", 1)[-1].rsplit(".", 1)[0] for x in r["related"]]
        assert len(stems) == len(set(s.lower() for s in stems))


def test_watcher_diff(tmp_path):
    from notesqa.watcher import vault_hashes, diff_vault
    (tmp_path / "a.md").write_text("one")
    h1 = vault_hashes(tmp_path)
    (tmp_path / "b.md").write_text("two")
    (tmp_path / "a.md").write_text("one edited")
    h2 = vault_hashes(tmp_path)
    added, changed, removed = diff_vault(h1, h2)
    assert added == ("b.md",) and changed == ("a.md",) and removed == ()
    (tmp_path / "b.md").unlink()
    added, changed, removed = diff_vault(h2, vault_hashes(tmp_path))
    assert removed == ("b.md",)
