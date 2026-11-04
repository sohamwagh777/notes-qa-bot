"""Minimal Streamlit interface for notes-qa-bot."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))
import streamlit as st
from notesqa.retrieve import retrieve
from notesqa.generate import answer
from notesqa.store import get_collection

st.title("Notes Q&A")
st.caption("100% local — your notes and questions never leave this machine.")
if st.button("Ingest data/vault"):
    from notesqa.store import sync_notes
    st.write(sync_notes(Path("data/vault")))

tags = sorted({t for m in get_collection().get(include=["metadatas"])["metadatas"]
               for t in m.get("tags", "").split(",") if t})
question = st.text_input("Ask your notes anything")
tag = st.selectbox("Tag filter", ["Any"] + tags)
if st.button("Ask", disabled=not question):
    with st.spinner("Searching your notes…"):
        rows = retrieve(question, tag=None if tag == "Any" else tag)
        result = answer(question, rows)
    st.subheader("Answer")
    st.write(result["answer"])
    if result["citations"]:
        st.subheader("Citations")
        for c in result["citations"]:
            st.write(f"[{c}]")
    if result["related"]:
        st.subheader("Related notes")
        for r in result["related"]:
            st.write(f"[{r}]")
