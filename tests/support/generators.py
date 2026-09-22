"""Hypothesis strategies that build **conforming** section files (§6).

Round-trip is only meaningful over files the format admits, so these strategies encode
the format's own constraints rather than generating arbitrary text:

* content lines never look like an anchor or a `^id` marker — FMT-02 gives the anchor no
  escape, so a paragraph containing a literal anchor line genuinely cannot be
  represented, and that is a property of the format, not a parser bug;
* no trailing whitespace, no tabs, no CR — FMT-09;
* a heading block is exactly one ATX line, per §6.3.
"""

from __future__ import annotations

from hypothesis import strategies as st

from specctl.ids import make_id, to_lower
from specctl.model import (
    TYPE_SPECS,
    Anchor,
    Block,
    FrontMatter,
    Section,
    SourceRef,
)

#: Latin, CJK, accents, punctuation — what an English translation of a Japanese spec
#: actually contains (see the §2.4 NG5 note).
TEXT_ALPHABET = st.characters(
    min_codepoint=0x20,
    max_codepoint=0x9FFF,
    blacklist_categories=("Cs", "Cc"),
    blacklist_characters="\t\r\n",
)

doc_keys = st.from_regex(r"\A[A-Z][A-Z0-9]{1,3}\Z")
counters = st.integers(min_value=1, max_value=999_999)


@st.composite
def block_ids(draw, doc_key: str | None = None) -> str:
    key = doc_key if doc_key is not None else draw(doc_keys)
    return make_id(key, draw(counters))


def _clean_line(raw: str) -> str:
    """Make a generated string usable as a content line (FMT-09, FMT-02)."""
    line = raw.replace("\t", " ").replace("\r", " ").replace("\n", " ").rstrip()
    if line.lstrip().startswith("<!--") or line.lstrip().startswith("^"):
        line = "x" + line
    return line


content_lines = st.text(TEXT_ALPHABET, min_size=0, max_size=60).map(_clean_line)


@st.composite
def anchors(draw, block_type: str | None = None, doc_key: str | None = None) -> Anchor:
    kind = block_type or draw(st.sampled_from(sorted(TYPE_SPECS)))
    spec = TYPE_SPECS[kind]
    attrs: dict[str, str] = {}
    for name in spec.required_attrs:
        attrs[name] = draw(_attr_values(name))
    for name in spec.optional_attrs:
        if draw(st.booleans()):
            attrs[name] = draw(_attr_values(name))
    if draw(st.booleans()):
        attrs["locked"] = draw(st.sampled_from(["true", "false"]))
    if kind != "heading" and draw(st.booleans()):
        # Lineage: either a merge or a split, never both on one block (§5.4).
        if draw(st.booleans()):
            count = draw(st.integers(min_value=1, max_value=3))
            attrs["supersedes"] = ",".join(draw(block_ids(doc_key)) for _ in range(count))
        else:
            attrs["split_from"] = draw(block_ids(doc_key))
    return Anchor(block_id=draw(block_ids(doc_key)), type=kind, attrs=attrs)


def _attr_values(name: str):
    if name == "ordered":
        return st.sampled_from(["true", "false"])
    if name == "format":
        return st.sampled_from(["pipe", "html", "latex", "image"])
    if name == "lang":
        return st.sampled_from(["c", "python", "text", "xml"])
    if name == "fallback":
        return st.just("true")
    if name == "asset":
        return st.from_regex(r"\A[A-Z]{3}-[0-9]{6}\.(png|xml|svg)\Z")
    if name == "reason":
        return st.sampled_from(
            ["shape_unrenderable", "table_parse_failed", "formula_conversion_failed"]
        )
    raise AssertionError(f"no strategy for attribute {name!r}")  # pragma: no cover


@st.composite
def heading_blocks(draw, level: int | None = None, doc_key: str | None = None) -> Block:
    depth = level if level is not None else draw(st.integers(min_value=1, max_value=6))
    number = draw(st.one_of(st.just(""), st.from_regex(r"\A[0-9]{1,2}(\.[0-9]{1,2}){0,3}\Z")))
    title = draw(st.text(TEXT_ALPHABET, min_size=1, max_size=40).map(_clean_line))
    title = title.strip() or "Untitled"
    prefix = f"{'#' * depth} "
    line = prefix + (f"{number} {title}" if number else title)
    anchor = draw(anchors(block_type="heading", doc_key=doc_key))
    return Block(anchor=anchor, lines=(line,), blockref=False)


@st.composite
def body_blocks(draw, doc_key: str | None = None) -> Block:
    anchor = draw(anchors(
        block_type=draw(st.sampled_from(
            ["paragraph", "list", "table", "figure", "formula", "code", "raw"]
        )),
        doc_key=doc_key,
    ))
    lines = draw(st.lists(content_lines, min_size=1, max_size=5))
    # Trailing blank lines are separation, not content (FMT-06); a canonical file has none.
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        lines = ["x"]
    return Block(anchor=anchor, lines=tuple(lines), blockref=draw(st.booleans()))


@st.composite
def front_matters(draw, section_id: str, doc_key: str) -> FrontMatter:
    origin = draw(st.sampled_from(["ingest", "authored"]))
    if origin == "ingest":
        start = draw(st.integers(min_value=0, max_value=5000))
        source = SourceRef(
            docx=draw(st.sampled_from(["source/SYS.docx", "source/other.docx"])),
            paragraphs=(start, start + draw(st.integers(min_value=0, max_value=50))),
        )
        bookmarks = tuple(draw(st.lists(
            st.from_regex(r"\A_(Ref|Toc)[0-9]{4,6}\Z"), max_size=3, unique=True
        )))
    else:
        source, bookmarks = None, ()
    return FrontMatter(
        id=section_id,
        doc=doc_key,
        number=draw(st.one_of(st.just(""), st.from_regex(r"\A[0-9]{1,2}(\.[0-9]{1,2})?\Z"))),
        title=draw(st.text(TEXT_ALPHABET, min_size=1, max_size=30)
                   .map(lambda s: s.strip() or "Untitled")),
        level=draw(st.integers(min_value=1, max_value=6)),
        order=draw(st.integers(min_value=0, max_value=200)),
        path=tuple(draw(st.lists(st.from_regex(r"\A[0-9]{1,2}\Z"), max_size=3))),
        path_ids=(section_id,),
        breadcrumb=draw(st.text(TEXT_ALPHABET, min_size=1, max_size=50)
                        .map(lambda s: s.strip() or "SYS")),
        bookmarks=bookmarks,
        refs_out=tuple(draw(st.lists(block_ids(doc_key), max_size=3, unique=True))),
        blocks=draw(st.integers(min_value=1, max_value=20)),
        words=draw(st.integers(min_value=0, max_value=5000)),
        origin=origin,
        source=source,
        ingest_version=1,
        generated=False,
        parent=draw(st.one_of(st.none(), block_ids(doc_key))),
    )


@st.composite
def sections(draw, doc_key: str | None = None) -> Section:
    """A conforming section: one heading block, then body blocks, all IDs distinct."""
    key = doc_key if doc_key is not None else draw(doc_keys)
    heading = draw(heading_blocks(doc_key=key))
    body = draw(st.lists(body_blocks(doc_key=key), min_size=0, max_size=4))

    seen = {heading.block_id}
    unique_body = []
    for block in body:
        if block.block_id in seen:
            continue
        seen.add(block.block_id)
        unique_body.append(block)

    front_matter = draw(front_matters(section_id=heading.block_id, doc_key=key))
    return Section(front_matter=front_matter, blocks=(heading, *unique_body))
