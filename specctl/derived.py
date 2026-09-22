"""Everything derived, computed in one place (§6.2, DEC-12, §11.3).

Front matter restates what the body already says: the heading line carries the number and
title, the document tree carries the parent and the breadcrumb, the blocks carry the
count and the word total. Anything restated will drift, and the agent navigates by the
restatement — a stale breadcrumb is a navigation error with no warning.

So the computation lives here, and the three commands that need it — the ingest writer
(§10.11), `fmt` (§11) and `index` (§13.2) — all call this rather than each implementing
it. Written three times it would be wrong in three different ways.

`parent`, `order`, `path`, `path_ids` and `breadcrumb` need the whole vault, not one
file, which is why every entry point here takes a `Document`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from .model import Document, FrontMatter, Section
from .textutil import split_heading_line, to_plain_text, words, wikilink_targets


@dataclass(frozen=True)
class Finding:
    """An observation made while recomputing. `fmt` and `validate` map these onto their
    own report formats (V15, and the `info` of §11.3)."""

    severity: str  # "info" | "warn"
    code: str
    section_id: str
    message: str


# --------------------------------------------------------------------------- ordering

def section_sort_key(section: Section) -> tuple[int, str]:
    """§11.3 — sections are ordered by their existing `order`, ties broken by file name.

    A total order, per the §9.5 determinism invariant: two sections can share an `order`
    only by mistake, and file name is unique because it is the section ID.
    """
    return (section.front_matter.order, section.filename)


def order_sections(document: Document) -> tuple[tuple[Section, ...], tuple[Finding, ...]]:
    """Put the vault in document order, reporting duplicated `order` values.

    §11.3: a section whose `order` is duplicated is placed after its predecessors in
    file-name order, and an `info` finding is reported.
    """
    ordered = tuple(sorted(document.sections, key=section_sort_key))
    findings: list[Finding] = []
    seen: dict[int, str] = {}
    for section in ordered:
        value = section.front_matter.order
        if value in seen:
            findings.append(Finding(
                "info", "duplicate_order", section.id,
                f"order {value} is also used by {seen[value]}; "
                "ordered by file name and renumbered",
            ))
        else:
            seen[value] = section.id
    return ordered, tuple(findings)


# --------------------------------------------------------------------------- the tree

@dataclass(frozen=True)
class Node:
    """A section's place in the document tree."""

    section: Section
    order: int
    level: int
    parent: str | None
    ancestors: tuple[Section, ...]  # root first, **including** the section itself


def build_tree(document: Document) -> tuple[tuple[Node, ...], tuple[Finding, ...]]:
    """Assign each section its parent and ancestor chain from heading levels.

    The parent is the nearest preceding section with a strictly smaller level. A section
    with no such predecessor — level 1, or the synthetic front-matter section at level 0
    (§10.9) — has no parent, and `parent` is then omitted from its front matter entirely
    rather than written as null (§6.2).
    """
    ordered, findings = order_sections(document)
    nodes: list[Node] = []
    stack: list[Node] = []  # ancestors of the section being placed, outermost first

    for index, section in enumerate(ordered):
        level = heading_level(section)
        while stack and stack[-1].level >= level:
            stack.pop()
        parent = stack[-1].section.id if stack else None
        ancestors = tuple(n.section for n in stack) + (section,)
        node = Node(section=section, order=index, level=level, parent=parent,
                    ancestors=ancestors)
        nodes.append(node)
        stack.append(node)
    return tuple(nodes), findings


def heading_level(section: Section) -> int:
    """The level the **body** states: the `#` count on the heading line (§6.2).

    Front matter is derived from the body, never the other way round, so a disagreement
    between them is drift that `fmt` corrects and V15 reports — not a fact to trust.
    The synthetic front-matter section has no `#` heading and stays at the level its
    front matter records (§10.9 gives it level 0).
    """
    lines = section.heading.lines
    if not lines:
        return section.front_matter.level
    try:
        level, _, _ = split_heading_line(lines[0])
    except ValueError:
        return section.front_matter.level
    return level


# --------------------------------------------------------------------------- the keys

def heading_parts(section: Section) -> tuple[str, str]:
    """(number, title) from the heading line (FMT-05)."""
    lines = section.heading.lines
    if not lines:
        return section.front_matter.number, section.front_matter.title
    try:
        _, number, title = split_heading_line(lines[0])
    except ValueError:
        return section.front_matter.number, section.front_matter.title
    return number, title


def breadcrumb_of(doc_key: str, ancestors: Sequence[Section]) -> str:
    """§6.2 — `doc` plus each ancestor's `number title` pair, `" > "`-separated.

    An unnumbered heading contributes its title alone, so the separator never doubles.
    """
    parts = [doc_key]
    for ancestor in ancestors:
        number, title = heading_parts(ancestor)
        parts.append(f"{number} {title}".strip())
    return " > ".join(parts)


def refs_out_of(section: Section) -> tuple[str, ...]:
    """§6.5 — every distinct wikilink target in the file, sorted ascending."""
    targets: set[str] = set()
    for block in section.blocks:
        targets.update(wikilink_targets(block.text))
    return tuple(sorted(targets))


def words_of(section: Section) -> int:
    """§6.2 — the §6.6 word count over `to_plain_text` of **all** blocks.

    One count over the concatenation, not a sum of per-block counts: the CJK term rounds
    up, so summing would round up once per block and inflate a section of short blocks.
    """
    joined = "\n".join(to_plain_text(block) for block in section.blocks)
    return words(joined)


def block_count_of(section: Section) -> int:
    """§6.2 — the anchor count in the file. Every block carries exactly one (FMT-02)."""
    return len(section.blocks)


def derive_front_matter(node: Node) -> FrontMatter:
    """Recompute every `fmt`-owned key, leaving the authored ones untouched.

    Authored and immutable: `id`, `doc`, `origin`, `source`, `bookmarks`,
    `ingest_version`, `generated` (§6.2). This function never touches them.
    """
    section = node.section
    current = section.front_matter
    number, title = heading_parts(section)
    return current.replace(
        number=number,
        title=title,
        level=node.level,
        parent=node.parent,
        order=node.order,
        path=tuple(heading_parts(a)[0] for a in node.ancestors),
        path_ids=tuple(a.id for a in node.ancestors),
        breadcrumb=breadcrumb_of(current.doc, node.ancestors),
        refs_out=refs_out_of(section),
        blocks=block_count_of(section),
        words=words_of(section),
    )


def recompute(document: Document) -> tuple[Document, tuple[Finding, ...]]:
    """Return the vault with every derived key recomputed, in document order.

    This is the single operation `fmt` performs on front matter, the ingest writer uses
    to fill it in the first place, and `index` reads to build the map.
    """
    nodes, findings = build_tree(document)
    sections = tuple(
        node.section.with_front_matter(derive_front_matter(node)) for node in nodes
    )
    return Document(sections=sections), findings


def drift(document: Document) -> tuple[Finding, ...]:
    """Which derived keys disagree with the body or the tree (V15).

    Read-only: this is what `validate` calls, and `validate` writes nothing (§12).
    """
    nodes, findings = build_tree(document)
    out = list(findings)
    for node in nodes:
        expected = derive_front_matter(node).to_mapping()
        actual = node.section.front_matter.to_mapping()
        for key in sorted(set(expected) | set(actual)):
            if expected.get(key) != actual.get(key):
                out.append(Finding(
                    "warn", "derived_drift", node.section.id,
                    f"{key}: front matter says {actual.get(key)!r}, "
                    f"the body says {expected.get(key)!r}",
                ))
    return tuple(out)
