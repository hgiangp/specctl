"""Derived front matter (§6.2, DEC-12, §11.3).

The agent navigates by `breadcrumb`, so a stale breadcrumb is a navigation error with no
warning. One implementation computes these keys; these tests are what keep it honest.
"""

from __future__ import annotations

import pytest

from specctl.derived import (
    breadcrumb_of,
    build_tree,
    derive_front_matter,
    drift,
    order_sections,
    recompute,
    refs_out_of,
    words_of,
)
from specctl.model import Anchor, Block, Document, FrontMatter, Section


def make_section(
    section_id: str, level: int, number: str, title: str, order: int,
    *body: Block, doc: str = "SYS", refs_out: tuple[str, ...] = (),
) -> Section:
    heading_line = f"{'#' * level} " + (f"{number} {title}" if number else title)
    heading = Block(anchor=Anchor(section_id, "heading"), lines=(heading_line,))
    return Section(
        front_matter=FrontMatter(
            id=section_id, doc=doc, number=number, title=title, level=level,
            order=order, path=(), path_ids=(section_id,), breadcrumb="",
            bookmarks=(), refs_out=refs_out, blocks=1 + len(body), words=0,
            origin="ingest", source=None, parent=None,
        ),
        blocks=(heading, *body),
    )


def para(block_id: str, *lines: str) -> Block:
    return Block(anchor=Anchor(block_id, "paragraph"), lines=lines)


@pytest.fixture
def vault() -> Document:
    """A three-level document: 3 -> 3.2 -> 3.2.1, plus a sibling at level 1."""
    return Document(sections=(
        make_section("SYS-000100", 1, "3", "Braking system", 0),
        make_section("SYS-000120", 2, "3.2", "Braking control", 1,
                     para("SYS-000121", "Torque within 50 ms per [[SYS-000245|5.1]].")),
        make_section("SYS-000140", 3, "3.2.1", "Pedal signal", 2),
        make_section("SYS-000200", 1, "4", "Diagnostics", 3),
    ))


# ------------------------------------------------------------------ the tree

def test_parent_is_the_nearest_shallower_predecessor(vault: Document) -> None:
    nodes, _ = build_tree(vault)
    parents = {n.section.id: n.parent for n in nodes}
    assert parents == {
        "SYS-000100": None,        # level 1 has no parent (§6.2)
        "SYS-000120": "SYS-000100",
        "SYS-000140": "SYS-000120",
        "SYS-000200": None,
    }


def test_a_level_one_section_omits_parent_entirely(vault: Document) -> None:
    """§6.2 — `parent` is absent at level 1, not written as null."""
    updated, _ = recompute(vault)
    root = updated.by_id()["SYS-000100"]
    assert root.front_matter.parent is None
    assert "parent" not in root.front_matter.to_mapping()


def test_the_synthetic_front_matter_section_is_a_level_one_sibling() -> None:
    """§10.9 as amended in v2.2 — the preamble is a real level-1 section with a `#` line.

    It must be a *sibling* of chapter 1, not its ancestor: the revision history is not
    chapter 3's parent, and at level 0 every breadcrumb in the vault would begin
    `SYS > Front matter >`.
    """
    preamble = make_section("SYS-000001", 1, "", "Front matter", 0)
    document = Document(sections=(preamble, make_section("SYS-000100", 1, "3", "B", 1)))
    nodes, _ = build_tree(document)
    assert [(n.section.id, n.level, n.parent) for n in nodes] == [
        ("SYS-000001", 1, None),
        ("SYS-000100", 1, None),
    ]
    updated, _ = recompute(document)
    assert updated.by_id()["SYS-000100"].front_matter.breadcrumb == "SYS > 3 B"


def test_a_heading_block_without_an_atx_line_is_refused_by_the_writer() -> None:
    """The level-0 bug, caught at the writer: a heading with no `#` line serializes to a
    line the parser reads as orphan content, so the section becomes unreadable."""
    from specctl.sectionfile import serialize_block

    empty = Block(anchor=Anchor("SYS-000001", "heading"), lines=())
    with pytest.raises(ValueError, match="exactly one ATX line"):
        serialize_block(empty)


def test_level_comes_from_the_body_not_the_front_matter() -> None:
    """Front matter is derived from the body, never the reverse — so a disagreement is
    drift that `fmt` corrects, not a fact to trust."""
    section = make_section("SYS-000120", 2, "3.2", "Braking control", 0)
    lying = section.with_front_matter(section.front_matter.replace(level=5))
    nodes, _ = build_tree(Document(sections=(lying,)))
    assert nodes[0].level == 2


def test_path_and_path_ids_include_the_section_itself(vault: Document) -> None:
    """§6.2 — `path_ids` ends with `id`; `path` is the matching number chain."""
    updated, _ = recompute(vault)
    deep = updated.by_id()["SYS-000140"].front_matter
    assert deep.path == ("3", "3.2", "3.2.1")
    assert deep.path_ids == ("SYS-000100", "SYS-000120", "SYS-000140")


def test_order_is_a_zero_based_index_in_document_order(vault: Document) -> None:
    updated, _ = recompute(vault)
    assert [s.front_matter.order for s in updated.sections] == [0, 1, 2, 3]


def test_duplicate_order_is_broken_by_file_name_and_reported() -> None:
    """§11.3 — placed after its predecessors in file-name order, with an `info` finding."""
    document = Document(sections=(
        make_section("SYS-000300", 1, "5", "Later", 7),
        make_section("SYS-000100", 1, "3", "Earlier", 7),
    ))
    ordered, findings = order_sections(document)
    assert [s.id for s in ordered] == ["SYS-000100", "SYS-000300"]
    assert [(f.severity, f.code) for f in findings] == [("info", "duplicate_order")]


# ------------------------------------------------------------------ breadcrumb

def test_breadcrumb_is_doc_then_each_ancestor(vault: Document) -> None:
    updated, _ = recompute(vault)
    assert updated.by_id()["SYS-000120"].front_matter.breadcrumb == (
        "SYS > 3 Braking system > 3.2 Braking control"
    )
    assert updated.by_id()["SYS-000140"].front_matter.breadcrumb == (
        "SYS > 3 Braking system > 3.2 Braking control > 3.2.1 Pedal signal"
    )


def test_an_unnumbered_heading_contributes_its_title_alone() -> None:
    """The separator must not double when a heading carries no number (§10.3 allows it)."""
    document = Document(sections=(make_section("SYS-000001", 1, "", "Revision history", 0),))
    updated, _ = recompute(document)
    assert updated.sections[0].front_matter.breadcrumb == "SYS > Revision history"


def test_breadcrumb_of_is_usable_on_its_own() -> None:
    ancestors = (
        make_section("SYS-000100", 1, "3", "Braking system", 0),
        make_section("SYS-000120", 2, "3.2", "Braking control", 1),
    )
    assert breadcrumb_of("SYS", ancestors) == "SYS > 3 Braking system > 3.2 Braking control"


def test_renaming_a_heading_updates_its_descendants_breadcrumbs(vault: Document) -> None:
    """T-FMT-01 — the case DEC-12 exists for: one edit, many derived keys."""
    sections = list(vault.sections)
    old = sections[1]
    sections[1] = old.with_blocks((
        old.heading.with_lines(("## 3.2 Brake actuation",)), *old.body,
    ))
    updated, _ = recompute(Document(sections=tuple(sections)))
    assert updated.by_id()["SYS-000120"].front_matter.title == "Brake actuation"
    assert "3.2 Brake actuation" in updated.by_id()["SYS-000140"].front_matter.breadcrumb


# ------------------------------------------------------------------ the other keys

def test_refs_out_is_deduplicated_and_sorted() -> None:
    """§6.5 — each distinct target exactly as written, sorted ascending."""
    section = make_section(
        "SYS-000120", 2, "3.2", "T", 0,
        para("SYS-000121", "[[SYS-000301#^sys-000302|x]] then [[SYS-000245|y]]"),
        para("SYS-000122", "again [[SYS-000245]]"),
    )
    assert refs_out_of(section) == ("SYS-000245", "SYS-000301#^sys-000302")


def test_blocks_is_the_anchor_count(vault: Document) -> None:
    updated, _ = recompute(vault)
    assert updated.by_id()["SYS-000120"].front_matter.blocks == 2  # heading + paragraph


def test_words_counts_the_concatenation_not_the_sum_of_blocks() -> None:
    """The CJK term rounds up, so summing per block would round up once per block and
    inflate a section of short blocks."""
    section = make_section(
        "SYS-000120", 2, "", "T", 0,
        para("SYS-000121", "一"), para("SYS-000122", "一"),
    )
    # heading "T" is 1 token; two CJK characters together are ceil(2/2.5) = 1
    assert words_of(section) == 2
    per_block_sum = 1 + 1 + 1
    assert words_of(section) < per_block_sum


def test_words_uses_plain_text_so_markup_is_not_counted() -> None:
    section = make_section(
        "SYS-000120", 2, "", "T", 0,
        para("SYS-000121", "see [[SYS-000245|the threshold]]"),
    )
    # "T" + "see the threshold" = 1 + 3; the target ID is not words
    assert words_of(section) == 4


def test_derive_leaves_authored_keys_untouched() -> None:
    """§6.2 — `id`, `doc`, `origin`, `source`, `bookmarks`, `ingest_version`,
    `generated` are authored at ingest and immutable."""
    section = make_section("SYS-000120", 2, "3.2", "T", 0)
    authored = section.front_matter.replace(
        bookmarks=("_Ref1",), origin="authored", source=None, ingest_version=1,
    )
    section = section.with_front_matter(authored)
    nodes, _ = build_tree(Document(sections=(section,)))
    derived = derive_front_matter(nodes[0])
    assert derived.bookmarks == ("_Ref1",)
    assert derived.origin == "authored"
    assert derived.source is None
    assert derived.doc == "SYS" and derived.id == "SYS-000120"


# ------------------------------------------------------------------ idempotence & drift

def test_recompute_is_idempotent(vault: Document) -> None:
    """`fmt` is idempotent (§9.5), and this is where that comes from."""
    once, _ = recompute(vault)
    twice, _ = recompute(once)
    assert once == twice


def test_drift_reports_a_stale_breadcrumb_and_writes_nothing(vault: Document) -> None:
    """V15. `validate` calls this, and `validate` writes nothing (§12)."""
    correct, _ = recompute(vault)
    sections = list(correct.sections)
    target = sections[1]
    sections[1] = target.with_front_matter(
        target.front_matter.replace(breadcrumb="SYS > wrong")
    )
    stale = Document(sections=tuple(sections))
    findings = drift(stale)
    assert any(f.code == "derived_drift" and "breadcrumb" in f.message for f in findings)
    assert stale.by_id()["SYS-000120"].front_matter.breadcrumb == "SYS > wrong"


def test_a_recomputed_vault_has_no_drift(vault: Document) -> None:
    correct, _ = recompute(vault)
    assert [f for f in drift(correct) if f.code == "derived_drift"] == []
