"""Block ID format and the two spellings of it (§5.1).

The ID is the only stable handle in the system (§5.3). Everything else — numbers, paths,
breadcrumbs, order — is derived and may change freely. So the format lives in one place
and every consumer asks here rather than carrying its own regular expression.
"""

from __future__ import annotations

import re

#: §5.1 — the canonical form. `SYS-000120`.
ID_RE = re.compile(r"^[A-Z][A-Z0-9]{1,7}-[0-9]{6}$")

#: §5.1 — the document key on its own, as supplied to `ingest --doc-key`.
DOC_KEY_RE = re.compile(r"^[A-Z][A-Z0-9]{1,7}$")

#: The lowercased form, used **only** in `^id` block-reference markers (FMT-04) and in
#: the fragment of a block-level wikilink (FMT-07).
LOWER_ID_RE = re.compile(r"^[a-z][a-z0-9]{1,7}-[0-9]{6}$")

COUNTER_WIDTH = 6


def is_id(value: str) -> bool:
    return bool(ID_RE.match(value))


def is_doc_key(value: str) -> bool:
    return bool(DOC_KEY_RE.match(value))


def make_id(doc_key: str, counter: int) -> str:
    """`SYS`, 120 → `SYS-000120`. Zero-padded to exactly six digits (§5.1)."""
    if not is_doc_key(doc_key):
        raise ValueError(f"not a document key: {doc_key!r} (must match {DOC_KEY_RE.pattern})")
    if not 0 <= counter < 10**COUNTER_WIDTH:
        raise ValueError(
            f"counter {counter} does not fit in {COUNTER_WIDTH} digits — "
            "IDs are never reused (§5.2), so the counter only grows"
        )
    return f"{doc_key}-{counter:0{COUNTER_WIDTH}d}"


def split_id(block_id: str) -> tuple[str, int]:
    """`SYS-000120` → (`SYS`, 120)."""
    if not is_id(block_id):
        raise ValueError(f"not a block ID: {block_id!r}")
    doc_key, _, counter = block_id.rpartition("-")
    return doc_key, int(counter)


def doc_key_of(block_id: str) -> str:
    return split_id(block_id)[0]


def counter_of(block_id: str) -> int:
    return split_id(block_id)[1]


def to_lower(block_id: str) -> str:
    """The `^id` / wikilink-fragment spelling: `SYS-000120` → `sys-000120` (§5.1)."""
    if not is_id(block_id):
        raise ValueError(f"not a block ID: {block_id!r}")
    return block_id.lower()


def from_lower(lower_id: str) -> str:
    """The inverse of `to_lower`."""
    if not LOWER_ID_RE.match(lower_id):
        raise ValueError(f"not a lowercased block ID: {lower_id!r}")
    return lower_id.upper()


def sort_key(block_id: str) -> tuple[str, int]:
    """A **total** order over IDs, per the §9.5 determinism invariant.

    Sorting IDs as plain strings works only while every counter has the same width. That
    is true today (always six digits) and this keeps it true if it ever stops being.
    """
    return split_id(block_id)
