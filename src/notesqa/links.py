"""Wikilink and backlink extraction."""
import re

def wikilinks(text):
    """Outgoing [[links]] in a note, de-duplicated, order preserved."""
    return list(dict.fromkeys(re.findall(r"\[\[([^\]|#]+)", text)))

def backlinks(name, notes):
    """Notes whose wikilinks point at `name` (matches on stem, case-insensitive)."""
    stem = name.rsplit(".", 1)[0].lower()
    return sorted(n for n, t in notes.items()
                  if any(l.strip().lower() in (stem, name.lower()) or
                         l.strip().lower().rsplit(".", 1)[0] == stem for l in wikilinks(t)))
